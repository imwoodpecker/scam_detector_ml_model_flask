"""
test_scam_detection.py

Comprehensive test cases for the scam detection pipeline.
Tests various scenarios including clean Hindi scams, Romanized Hinglish, noisy audio, and normal conversations.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from audio_risk_pipeline import analyze_audio
from transcript_quality import assess_transcript_quality
from text_normalizer import normalize_text_for_scoring, create_multilingual_keyword_map


class TestScamDetection(unittest.TestCase):
    """Test cases for scam detection pipeline."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temp files if needed
        pass

    def test_clean_hindi_scam_detection(self):
        """Test detection of clean Hindi scam call."""
        # Mock audio preprocessing
        mock_audio_path = os.path.join(self.temp_dir, "test_hindi.wav")
        
        # Mock STT segments for Hindi scam
        mock_segments = [
            {"start": 0.0, "end": 3.0, "text": "नमस्ते मैं बैंक से बोल रहा हूँ"},
            {"start": 3.0, "end": 6.0, "text": "आपका अकाउंट ब्लॉक हो जाएगा"},
            {"start": 6.0, "end": 9.0, "text": "ओटीपी बताइए अभी"},
            {"start": 9.0, "end": 12.0, "text": "किसी को मत बताना"},
        ]
        
        mock_stt_meta = {
            "backend": "faster_whisper",
            "language": "hi",
            "language_probability": 0.95
        }
        
        with patch('audio_risk_pipeline.preprocess_audio') as mock_preprocess, \
             patch('audio_risk_pipeline.get_audio_metrics') as mock_metrics, \
             patch('audio_risk_pipeline.transcribe_file_with_meta') as mock_transcribe, \
             patch('audio_risk_pipeline.diarize_segments') as mock_diarize, \
             patch('audio_risk_pipeline.analyze_conversation') as mock_analyze, \
             patch('audio_risk_pipeline.cleanup_processed_audio'):
            
            mock_preprocess.return_value = mock_audio_path
            mock_metrics.return_value = {"duration_seconds": 12.0, "snr_estimate_db": 25.0}
            mock_transcribe.return_value = (mock_segments, mock_stt_meta)
            mock_diarize.return_value = mock_segments
            mock_analyze.return_value = {
                "urgency_phrase_count": 2,
                "otp_credential_mentions": 1,
                "authority_impersonation_signals": 1,
                "secrecy_mentions": 1
            }
            
            result = analyze_audio("dummy_audio.mp3")
            
            # Should detect HIGH risk
            self.assertEqual(result["risk_level"], "HIGH")
            self.assertGreaterEqual(result["risk_score"], 70)
            self.assertEqual(result["transcript_quality"]["is_sufficient_for_scoring"], True)
            self.assertIn("authority_impersonation_signals", result["details"]["features"])
            self.assertIn("otp_credential_mentions", result["details"]["features"])

    def test_romanized_hinglish_scam(self):
        """Test detection of Romanized Hinglish scam."""
        mock_audio_path = os.path.join(self.temp_dir, "test_hinglish.wav")
        
        mock_segments = [
            {"start": 0.0, "end": 3.0, "text": "hello I am calling from bank"},
            {"start": 3.0, "end": 6.0, "text": "your account will be blocked immediately"},
            {"start": 6.0, "end": 9.0, "text": "otp bataye abhi"},
            {"start": 9.0, "end": 12.0, "text": "kisi ko mat batao please"},
        ]
        
        mock_stt_meta = {
            "backend": "faster_whisper",
            "language": "hi",
            "language_probability": 0.85
        }
        
        with patch('audio_risk_pipeline.preprocess_audio') as mock_preprocess, \
             patch('audio_risk_pipeline.get_audio_metrics') as mock_metrics, \
             patch('audio_risk_pipeline.transcribe_file_with_meta') as mock_transcribe, \
             patch('audio_risk_pipeline.diarize_segments') as mock_diarize, \
             patch('audio_risk_pipeline.analyze_conversation') as mock_analyze, \
             patch('audio_risk_pipeline.cleanup_processed_audio'):
            
            mock_preprocess.return_value = mock_audio_path
            mock_metrics.return_value = {"duration_seconds": 12.0, "snr_estimate_db": 20.0}
            mock_transcribe.return_value = (mock_segments, mock_stt_meta)
            mock_diarize.return_value = mock_segments
            mock_analyze.return_value = {
                "urgency_phrase_count": 2,
                "otp_credential_mentions": 1,
                "authority_impersonation_signals": 1,
                "secrecy_mentions": 1
            }
            
            result = analyze_audio("dummy_audio.mp3")
            
            # Should detect HIGH risk
            self.assertEqual(result["risk_level"], "HIGH")
            self.assertGreaterEqual(result["risk_score"], 70)
            self.assertEqual(result["transcript_quality"]["is_sufficient_for_scoring"], True)

    def test_noisy_unclear_audio(self):
        """Test handling of noisy/unclear audio."""
        mock_audio_path = os.path.join(self.temp_dir, "test_noisy.wav")
        
        # Mock very poor quality segments
        mock_segments = [
            {"start": 0.0, "end": 2.0, "text": "uh"},
            {"start": 2.0, "end": 4.0, "text": "mm"},
            {"start": 4.0, "end": 6.0, "text": "hello"},
        ]
        
        mock_stt_meta = {
            "backend": "faster_whisper",
            "language": "en",
            "language_probability": 0.3
        }
        
        with patch('audio_risk_pipeline.preprocess_audio') as mock_preprocess, \
             patch('audio_risk_pipeline.get_audio_metrics') as mock_metrics, \
             patch('audio_risk_pipeline.transcribe_file_with_meta') as mock_transcribe, \
             patch('audio_risk_pipeline.cleanup_processed_audio'):
            
            mock_preprocess.return_value = mock_audio_path
            mock_metrics.return_value = {"duration_seconds": 6.0, "snr_estimate_db": 5.0}
            mock_transcribe.return_value = (mock_segments, mock_stt_meta)
            
            result = analyze_audio("dummy_audio.mp3")
            
            # Should return UNKNOWN due to poor quality
            self.assertEqual(result["risk_level"], "UNKNOWN")
            self.assertIsNone(result["risk_score"])
            self.assertEqual(result["transcript_quality"]["is_sufficient_for_scoring"], False)
            self.assertIn("transcript_quality_insufficient", result["flags"])

    def test_normal_conversation(self):
        """Test handling of normal conversation."""
        mock_audio_path = os.path.join(self.temp_dir, "test_normal.wav")
        
        mock_segments = [
            {"start": 0.0, "end": 5.0, "text": "Hi, how are you doing today?"},
            {"start": 5.0, "end": 10.0, "text": "I'm doing well, thanks for asking"},
            {"start": 10.0, "end": 15.0, "text": "What time is our meeting tomorrow?"},
            {"start": 15.0, "end": 20.0, "text": "The meeting is at 2 PM in the main conference room"},
        ]
        
        mock_stt_meta = {
            "backend": "faster_whisper",
            "language": "en",
            "language_probability": 0.98
        }
        
        with patch('audio_risk_pipeline.preprocess_audio') as mock_preprocess, \
             patch('audio_risk_pipeline.get_audio_metrics') as mock_metrics, \
             patch('audio_risk_pipeline.transcribe_file_with_meta') as mock_transcribe, \
             patch('audio_risk_pipeline.diarize_segments') as mock_diarize, \
             patch('audio_risk_pipeline.analyze_conversation') as mock_analyze, \
             patch('audio_risk_pipeline.cleanup_processed_audio'):
            
            mock_preprocess.return_value = mock_audio_path
            mock_metrics.return_value = {"duration_seconds": 20.0, "snr_estimate_db": 30.0}
            mock_transcribe.return_value = (mock_segments, mock_stt_meta)
            mock_diarize.return_value = mock_segments
            mock_analyze.return_value = {
                "urgency_phrase_count": 0,
                "otp_credential_mentions": 0,
                "authority_impersonation_signals": 0,
                "secrecy_mentions": 0
            }
            
            result = analyze_audio("dummy_audio.mp3")
            
            # Should detect LOW risk
            self.assertEqual(result["risk_level"], "LOW")
            self.assertLess(result["risk_score"], 40)
            self.assertEqual(result["transcript_quality"]["is_sufficient_for_scoring"], True)

    def test_tamil_scam_detection(self):
        """Test detection of Tamil scam call."""
        mock_audio_path = os.path.join(self.temp_dir, "test_tamil.wav")
        
        mock_segments = [
            {"start": 0.0, "end": 3.0, "text": "வணக்கம் நான் வங்கியிலிருந்து அழைக்கிறேன்"},
            {"start": 3.0, "end": 6.0, "text": "உங்க அக்கவுண்ட் ப்ளாக் ஆகும்"},
            {"start": 6.0, "end": 9.0, "text": "ஓடிபி சொல்லுங்க உடனே"},
            {"start": 9.0, "end": 12.0, "text": "யாருக்கும் சொல்லாதே"},
        ]
        
        mock_stt_meta = {
            "backend": "faster_whisper",
            "language": "ta",
            "language_probability": 0.92
        }
        
        with patch('audio_risk_pipeline.preprocess_audio') as mock_preprocess, \
             patch('audio_risk_pipeline.get_audio_metrics') as mock_metrics, \
             patch('audio_risk_pipeline.transcribe_file_with_meta') as mock_transcribe, \
             patch('audio_risk_pipeline.diarize_segments') as mock_diarize, \
             patch('audio_risk_pipeline.analyze_conversation') as mock_analyze, \
             patch('audio_risk_pipeline.cleanup_processed_audio'):
            
            mock_preprocess.return_value = mock_audio_path
            mock_metrics.return_value = {"duration_seconds": 12.0, "snr_estimate_db": 25.0}
            mock_transcribe.return_value = (mock_segments, mock_stt_meta)
            mock_diarize.return_value = mock_segments
            mock_analyze.return_value = {
                "urgency_phrase_count": 2,
                "otp_credential_mentions": 1,
                "authority_impersonation_signals": 1,
                "secrecy_mentions": 1
            }
            
            result = analyze_audio("dummy_audio.mp3")
            
            # Should detect HIGH risk
            self.assertEqual(result["risk_level"], "HIGH")
            self.assertGreaterEqual(result["risk_score"], 70)
            self.assertEqual(result["transcript_quality"]["is_sufficient_for_scoring"], True)

    def test_transcript_quality_assessment(self):
        """Test transcript quality assessment function."""
        # Test good quality transcript
        good_text = "Hello I am calling from your bank. Your account will be blocked if you don't provide the OTP immediately."
        good_segments = [
            {"start": 0.0, "end": 3.0, "text": "Hello I am calling from your bank."},
            {"start": 3.0, "end": 6.0, "text": "Your account will be blocked if you don't provide the OTP immediately."}
        ]
        
        result = assess_transcript_quality(good_text, good_segments)
        
        self.assertEqual(result["is_sufficient_for_scoring"], True)
        self.assertGreater(result["quality_score"], 0.5)
        self.assertEqual(result["recommendation"], "PROCEED")
        
        # Test poor quality transcript
        poor_text = "uh mm hello uh"
        poor_segments = [
            {"start": 0.0, "end": 1.0, "text": "uh"},
            {"start": 1.0, "end": 2.0, "text": "mm"},
            {"start": 2.0, "end": 3.0, "text": "hello"},
            {"start": 3.0, "end": 4.0, "text": "uh"}
        ]
        
        result = assess_transcript_quality(poor_text, poor_segments)
        
        self.assertEqual(result["is_sufficient_for_scoring"], False)
        self.assertLess(result["quality_score"], 0.5)
        self.assertEqual(result["recommendation"], "REJECT")

    def test_text_normalization(self):
        """Test text normalization for multi-language support."""
        # Test ASR error correction
        text_with_errors = "o t p please tell me the o t p"
        normalized = normalize_text_for_scoring(text_with_errors)
        self.assertIn("otp", normalized)
        
        # Test Hinglish normalization
        hinglish_text = "otp bataye abhi please"
        normalized = normalize_text_for_scoring(hinglish_text, "hi")
        self.assertIn("otp bataye", normalized.lower())
        
        # Test Tamil normalization
        tamil_text = "otp sollunga ippove"
        normalized = normalize_text_for_scoring(tamil_text, "ta")
        self.assertIn("otp sollunga", normalized.lower())
        
        # Test mixed script handling
        mixed_text = "ओटीपी बताइए otp bataye"
        normalized = normalize_text_for_scoring(mixed_text, "hi")
        self.assertTrue("otp" in normalized.lower() or "ओटीपी" in normalized)

    def test_multilingual_keyword_expansion(self):
        """Test multilingual keyword expansion."""
        from text_normalizer import expand_keywords_with_variants
        
        # Test basic keyword expansion
        keywords = {"otp", "urgent"}
        expanded = expand_keywords_with_variants(keywords)
        
        # Should include variants in multiple languages
        self.assertIn("otp", expanded)
        self.assertIn("o t p", expanded)
        self.assertIn("ओटीपी", expanded)
        self.assertIn("ஓடிபி", expanded)
        self.assertIn("ఓటిపి", expanded)
        self.assertIn("ഓടിപി", expanded)
        
        # Should include urgency variants
        self.assertIn("urgent", expanded)
        self.assertIn("अभी", expanded)
        self.assertIn("உடனே", expanded)
        self.assertIn("వెంటనే", expanded)
        self.assertIn("ഉടനെ", expanded)

    def test_audio_preprocessing_failure(self):
        """Test handling of audio preprocessing failure."""
        with patch('audio_risk_pipeline.preprocess_audio') as mock_preprocess:
            mock_preprocess.side_effect = Exception("Audio file corrupted")
            
            result = analyze_audio("corrupted_audio.mp3")
            
            # Should return UNKNOWN with preprocessing error
            self.assertEqual(result["risk_level"], "UNKNOWN")
            self.assertIsNone(result["risk_score"])
            self.assertEqual(result["transcript_quality"]["is_sufficient_for_scoring"], False)
            self.assertIn("audio_preprocessing_failed", result["flags"])
            self.assertIn("Audio preprocessing failed", result["transcript_quality"]["explanation"])

    def test_output_contract_compliance(self):
        """Test that output complies with the specified contract."""
        mock_audio_path = os.path.join(self.temp_dir, "test_contract.wav")
        
        mock_segments = [
            {"start": 0.0, "end": 3.0, "text": "Hello from bank"},
        ]
        
        mock_stt_meta = {
            "backend": "faster_whisper",
            "language": "en",
            "language_probability": 0.9
        }
        
        with patch('audio_risk_pipeline.preprocess_audio') as mock_preprocess, \
             patch('audio_risk_pipeline.get_audio_metrics') as mock_metrics, \
             patch('audio_risk_pipeline.transcribe_file_with_meta') as mock_transcribe, \
             patch('audio_risk_pipeline.diarize_segments') as mock_diarize, \
             patch('audio_risk_pipeline.analyze_conversation') as mock_analyze, \
             patch('audio_risk_pipeline.cleanup_processed_audio'):
            
            mock_preprocess.return_value = mock_audio_path
            mock_metrics.return_value = {"duration_seconds": 3.0, "snr_estimate_db": 25.0}
            mock_transcribe.return_value = (mock_segments, mock_stt_meta)
            mock_diarize.return_value = mock_segments
            mock_analyze.return_value = {}
            
            result = analyze_audio("dummy_audio.mp3")
            
            # Check required fields are present
            required_fields = [
                "risk_score", "risk_level", "transcript_quality", 
                "audio_quality", "stt_backend", "flags", "summary"
            ]
            
            for field in required_fields:
                self.assertIn(field, result)
            
            # Check risk_level is valid
            valid_risk_levels = ["LOW", "MEDIUM", "HIGH", "UNKNOWN"]
            self.assertIn(result["risk_level"], valid_risk_levels)
            
            # Check transcript_quality structure
            quality_fields = [
                "quality_score", "quality_level", "is_sufficient_for_scoring",
                "explanation", "recommendation"
            ]
            
            for field in quality_fields:
                self.assertIn(field, result["transcript_quality"])
            
            # Check stt_backend structure
            backend_fields = ["backend", "model", "language", "language_probability"]
            for field in backend_fields:
                self.assertIn(field, result["stt_backend"])


if __name__ == "__main__":
    unittest.main()
