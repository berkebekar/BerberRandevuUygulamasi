import { initializeApp, getApps } from "firebase/app"
import { getAuth } from "firebase/auth"

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
}

export function getFirebaseAuth() {
  const missingConfig = Object.entries(firebaseConfig).some(([, value]) => !value)
  if (missingConfig) {
    throw new Error("Firebase ayarlari eksik.")
  }

  const app = getApps().length > 0 ? getApps()[0] : initializeApp(firebaseConfig)
  const auth = getAuth(app)
  auth.languageCode = "tr"
  return auth
}
