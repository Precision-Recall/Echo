import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyCIa9xq_WbAEnCElCFrm0U-DpNgrlVfooQ",
  authDomain: "echooo-482613.firebaseapp.com",
  projectId: "echooo-482613",
  storageBucket: "echooo-482613.firebasestorage.app",
  messagingSenderId: "572734224282",
  appId: "1:572734224282:web:1fa5197805471431fe2c23"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firebase Authentication and get a reference to the service
export const auth = getAuth(app);
export default app;

