import librosa
import numpy as np
import joblib
import os


class ScamDetector:
    def __init__(self):
        """
        Load model once when API starts
        """
        model_path = "scam_model.pkl"

        if os.path.exists(model_path):
            self.model = joblib.load(model_path)
        else:
            # If model not found, run in dummy mode
            self.model = None

    def extract_features(self, audio_path):
        """
        Extract MFCC features from audio
        """
        y, sr = librosa.load(audio_path, sr=None)

        mfcc = librosa.feature.mfcc(
            y=y,
            sr=sr,
            n_mfcc=40
        )

        mfcc_mean = np.mean(mfcc.T, axis=0)
        return mfcc_mean.reshape(1, -1)

    def predict(self, audio_path):
        """
        Main prediction function
        """
        features = self.extract_features(audio_path)

        # If trained model exists
        if self.model:
            prob = self.model.predict_proba(features)[0]
            scam_prob = float(prob[1])
        else:
            # Dummy fallback (for testing)
            scam_prob = float(np.random.uniform(0.6, 0.95))

        label = "Scam" if scam_prob > 0.5 else "Not Scam"

        return {
            "label": label,
            "confidence": round(scam_prob, 2)
        }

