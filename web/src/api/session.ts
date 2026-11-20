// The access token lives in sessionStorage: it is gone when the tab closes (tokens last 60 minutes,
// no refresh token yet). Mock mode stores a fake token the same way.
const KEY = "rh-token";
export const getToken = (): string | null => {
  try {
    return window.sessionStorage.getItem(KEY);
  } catch {
    return null;
  }
};
export const setToken = (t: string) => {
  try {
    window.sessionStorage.setItem(KEY, t);
  } catch {
    /* ignore */
  }
};
export const clearToken = () => {
  try {
    window.sessionStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
};
