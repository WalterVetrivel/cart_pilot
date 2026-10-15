import { GoogleAuthProvider, reauthenticateWithPopup } from 'firebase/auth'
import { auth, gmailProvider } from './firebase'

const MESSAGES: Record<string, string> = {
  'auth/popup-closed-by-user': 'Gmail wasn’t connected: the Google window was closed.',
  'auth/cancelled-popup-request': 'Gmail wasn’t connected: the Google window was closed.',
  'auth/popup-blocked': 'Your browser blocked the Google window. Allow pop-ups for this site and try again.',
  'auth/user-mismatch': 'Choose the same Google account you signed in with.',
}

/**
 * Asks Google for a read-only Gmail token for the signed-in account (SPEC §11).
 * Re-authenticating, rather than signing in again, keeps the user on the same account.
 * The token is returned to the caller to send once to the backend; it is never stored.
 */
export async function requestGmailToken(): Promise<string> {
  const user = auth?.currentUser
  if (!user) throw new Error('Sign in with Google to connect Gmail.')
  const provider = gmailProvider()
  if (user.email) provider.setCustomParameters({ login_hint: user.email })
  try {
    const result = await reauthenticateWithPopup(user, provider)
    const token = GoogleAuthProvider.credentialFromResult(result)?.accessToken
    if (!token) throw new Error('Google didn’t grant Gmail access. Try again and allow “Read your email”.')
    return token
  } catch (e) {
    const code = (e as { code?: string }).code
    throw new Error((code && MESSAGES[code]) || (e as Error).message, { cause: e })
  }
}
