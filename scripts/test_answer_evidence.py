"""Regression tests for lost option definitions and unsupported factual answers."""

import unittest
from unittest.mock import patch

from answer import format_excerpts_block, generate_answer, generate_answer_streaming, lookup_option_definition, select_evidence_window


class EvidenceTests(unittest.TestCase):
    @patch("answer.ollama.Client")
    def test_exact_option_lookup_does_not_invent_examples_or_call_a_model(self, client: object) -> None:
        chunks = [{"chunk_text": "SERVICE/VERSION DETECTION:\n  -sV: Probe open ports to determine service/version info"}]
        answer = generate_answer("What does nmap -sV do?", chunks, route="kali_docs")
        self.assertIn("Probe open ports to determine service/version info [1]", answer)
        self.assertEqual(list(generate_answer_streaming("Explain -sV", chunks, route="kali_docs")), [("token", answer)])
        client.assert_not_called()

    def test_conflicting_definitions_are_not_silently_resolved(self) -> None:
        chunks = [{"chunk_text": "-x: one meaning"}, {"chunk_text": "-x: a conflicting meaning"}]
        self.assertIsNone(lookup_option_definition("What does -x do?", chunks))

    def test_option_matching_preserves_case(self) -> None:
        self.assertIsNone(lookup_option_definition("Explain -sv", [{"chunk_text": "-sV: Version detection"}]))

    def test_option_definition_survives_a_long_document_header(self) -> None:
        text = "Introduction and host discovery.\n" * 60 + "-sV: Probe open ports to determine service/version info\n"
        window = select_evidence_window(text, "What does nmap -sV do?")
        self.assertIn("-sV: Probe open ports", window)
        self.assertLessEqual(len(window), 500)

    def test_short_evidence_is_not_rewritten(self) -> None:
        text = "-sV: Probe open ports to determine service/version info"
        self.assertEqual(select_evidence_window(text, "nmap -sV"), text)

    def test_numbered_citation_and_requested_definition_are_kept(self) -> None:
        chunks = [{"file_name": "nmap.txt", "chunk_text": "header\n" * 200 + "-sV: Version detection"}]
        block = format_excerpts_block(chunks, "Explain -sV")
        self.assertIn("[1] nmap.txt", block)
        self.assertIn("-sV: Version detection", block)

    @patch("answer.ollama.Client")
    def test_missing_evidence_does_not_call_the_model(self, client: object) -> None:
        text = generate_answer("What is my device firmware version?", [], route="local_file")
        self.assertTrue(text.startswith("UNKNOWN"))
        self.assertIn("Confidence: Low", text)
        client.assert_not_called()

    @patch("answer.ollama.Client")
    def test_streaming_missing_evidence_matches_non_streaming(self, client: object) -> None:
        chunks = [{"chunk_text": "  "}]
        expected = generate_answer("Which firmware?", chunks, route="local_file")
        events = list(generate_answer_streaming("Which firmware?", chunks, route="local_file"))
        self.assertEqual(events, [("token", expected)])
        client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
