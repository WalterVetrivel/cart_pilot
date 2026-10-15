import { initializeApp, type FirebaseApp } from 'firebase/app'
import { getAuth, GoogleAuthProvider, type Auth } from 'firebase/auth'

const config = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
}

/** True when the VITE_FIREBASE_* variables are present (see .env.example). */
export const firebaseConfigured = Boolean(config.apiKey && config.projectId)

export const app: FirebaseApp | null = firebaseConfigured ? initializeApp(config) : null
export const auth: Auth | null = app ? getAuth(app) : null

export const googleProvider = new GoogleAuthProvider()

/** Separate provider used only on "Connect Gmail" (SPEC §11); token is never persisted. */
export function gmailProvider(): GoogleAuthProvider {
  const provider = new GoogleAuthProvider()
  provider.addScope('https://www.googleapis.com/auth/gmail.readonly')
  return provider
}
