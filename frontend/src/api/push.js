// Phone and desktop notifications (Web Push). The browser subscribes with the
// backend's public key; the backend then sends tomorrow's briefing, NO-GO warnings
// and new hazard reports for your site, and the service worker (public/sw.js)
// shows them even when the app is closed. Each device is turned on separately.
import { apiRequest, USE_MOCKS } from './client.js';
import { ENDPOINTS } from './endpoints.js';
import { base64UrlToBytes, sameBytes } from '../utils/encoding.js';

const isIos = () => /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
const isHomeScreenApp = () => window.matchMedia?.('(display-mode: standalone)').matches || navigator.standalone === true;

/** Why notifications can't be turned on here, or null when they can. */
export function pushUnavailableReason() {
  if (USE_MOCKS) return 'Notifications need the live backend (this is demo data).';
  if (!window.isSecureContext) {
    return 'Notifications need a secure connection. Open the app at its https link (or at localhost on this computer).';
  }
  if (isIos() && !isHomeScreenApp()) {
    return 'On iPhone and iPad: tap Share, then "Add to Home Screen", open PlanIT from the Home Screen and turn notifications on there.';
  }
  if (!('serviceWorker' in navigator) || !('PushManager' in window) || !('Notification' in window)) {
    return "This browser doesn't support notifications.";
  }
  return null;
}

/** The service worker that receives pushes (registered in offline.js); fails instead of waiting forever. */
async function worker() {
  const timeout = new Promise((_, reject) =>
    setTimeout(() => reject(new Error("The notification service isn't ready. Reload the page and try again.")), 8000),
  );
  return Promise.race([navigator.serviceWorker.ready, timeout]);
}

/** 'on' | 'off' | 'blocked' | 'unavailable' for this device. */
export async function getPushStatus() {
  if (pushUnavailableReason()) return 'unavailable';
  if (Notification.permission === 'denied') return 'blocked';
  const subscription = await (await worker()).pushManager.getSubscription();
  return subscription && Notification.permission === 'granted' ? 'on' : 'off';
}

/** Ask for permission, subscribe this browser and register it with the backend. */
export async function enablePush() {
  const reason = pushUnavailableReason();
  if (reason) throw new Error(reason);
  const permission = await Notification.requestPermission();
  if (permission !== 'granted') {
    throw new Error(
      permission === 'denied'
        ? 'Notifications are blocked for this site. Allow them in your browser or phone settings, then try again.'
        : 'Notifications were not allowed.',
    );
  }
  const registration = await worker();
  const { publicKey } = await apiRequest(ENDPOINTS.push.key); // REST API PLACEHOLDER: GET /api/push/key
  const serverKey = base64UrlToBytes(publicKey);
  let subscription = await registration.pushManager.getSubscription();
  // A subscription made with an older server key can't receive our messages: replace it.
  if (subscription && subscription.options?.applicationServerKey && !sameBytes(subscription.options.applicationServerKey, serverKey)) {
    await subscription.unsubscribe();
    subscription = null;
  }
  subscription ??= await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: serverKey });
  // REST API PLACEHOLDER: POST /api/push/subscriptions
  await apiRequest(ENDPOINTS.push.subscriptions, { method: 'POST', body: subscription.toJSON() });
  return 'on';
}

/** Stop notifications on this device. */
export async function disablePush() {
  const subscription = await (await worker()).pushManager.getSubscription();
  if (subscription) {
    // REST API PLACEHOLDER: DELETE /api/push/subscriptions
    await apiRequest(ENDPOINTS.push.subscriptions, { method: 'DELETE', body: { endpoint: subscription.endpoint } }).catch(() => {});
    await subscription.unsubscribe();
  }
  return 'off';
}

/** On sign-out: so the next person on a shared device doesn't get this account's notifications. */
export async function forgetThisDevice() {
  if (USE_MOCKS || !('serviceWorker' in navigator)) return;
  const registration = await navigator.serviceWorker.getRegistration();
  const subscription = await registration?.pushManager?.getSubscription();
  if (!subscription) return;
  await apiRequest(ENDPOINTS.push.subscriptions, { method: 'DELETE', body: { endpoint: subscription.endpoint } }).catch(() => {});
  await subscription.unsubscribe().catch(() => {});
}

/**
 * Send yourself a test notification on every device that has notifications on.
 * REST API PLACEHOLDER: POST /api/push/test  -> { message, devices }
 */
export const sendTestPush = () => apiRequest(ENDPOINTS.push.test, { method: 'POST' });
