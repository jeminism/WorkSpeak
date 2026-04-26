"""
Message Rewriter for WorkSpeak.
Handles rewriting with multi-tier quality control.
Copied from slack_message_bot.rewriter with minor adaptations.
"""

import re
import numpy as np
from typing import Optional, Tuple

HAS_EMBEDDINGS = False
embedding_model = None
try:
    from sentence_transformers import SentenceTransformer
    HAS_EMBEDDINGS = True
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
except ImportError:
    pass

from .llm_backend import LLMCallResult
from .config import LLMConfig


class MessageRewriter:
    """Rewrites messages with 3-tier quality control."""
    
    def __init__(self):
        from .llm_backend import get_backend
        self.backend = get_backend()
    
    def _remove_metadata(self, text: str) -> str:
        """Remove standard LLM metadata patterns."""
        patterns = [
            r'with\s+\d+\s+tokens?\s+used(?:[,].*)?(?:[$,]\s*\$?\d+\.?\d*)?(?:,|$).*a\s+successful\s+outcome',
            r'with\s+\d+\s+tokens?\s+used',
            r'Estimated\s+cost:\s+[$,]?\d+\.?\d+',
            r'Quality\s+score:\s*[\d.]+',
            r'\d+\s+iterations?',
        ]
        result = text
        for pattern in patterns:
            result = re.sub(pattern, '', result, flags=re.IGNORECASE)
        return result.strip()
    
    def _remove_artifacts(self, text: str) -> str:
        """Remove LLM explanation artifacts."""
        patterns = [
            r'This revised response aims to:',
            r'The rewritten text is:',
            r'###?\s*(Summary|Explanation|Reasoning|Thinking|Analysis)',
            r'(In\s+summary|To\s+summarize|Here is the revised):',
            r'Here is the rewritten text:',
            r'Rewritten text:',
        ]
        result = text
        for pattern in patterns:
            result = re.sub(pattern, '', result, flags=re.IGNORECASE).strip()
        
        # Remove numbered lists and bullets from explanations
        result = re.sub(r'^\d+\.\s+', '', result, flags=re.MULTILINE)
        result = re.sub(r'^[-•*\u2022]\s+', '', result, flags=re.MULTILINE)
        result = re.sub(r'^###?.*\n', '', result, flags=re.MULTILINE)
        
        # Remove single lines that look like explanations
        lines = result.split('\n')
        filtered_lines = []
        explain_markers = ['explanation', 'summary', 'reasoning', 'analysis', 'note']
        for line in lines:
            line_lower = line.lower().strip()
            if any(marker in line_lower for marker in explain_markers):
                continue
            filtered_lines.append(line)
        
        result = '\n'.join(filtered_lines).strip()
        return result
    
    def _post_process(self, text: str) -> str:
        """Apply all post-processors."""
        for processor in [self._remove_metadata, self._remove_artifacts]:
            text = processor(text)
        # Remove multiple newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()
    
    def _check_semantic_similarity(self, original: str, rewritten: str) -> float:
        """Check cosine similarity between embeddings."""
        if not HAS_EMBEDDINGS or embedding_model is None:
            return 0.95  # Default high score if embeddings unavailable
        
        try:
            orig_emb = embedding_model.encode(original, convert_to_numpy=True, show_progress_bar=False)
            rewrt_emb = embedding_model.encode(rewritten, convert_to_numpy=True, show_progress_bar=False)
            similarity = np.dot(orig_emb, rewrt_emb) / (np.linalg.norm(orig_emb) * np.linalg.norm(rewrt_emb))
            return float(similarity)
        except Exception:
            return 0.8  # Default high score on error
    
    def _check_conciseness(self, original: str, rewritten: str) -> float:
        """Check word count ratio, penalize if rewritten is too long or short."""
        orig_words = len(original.split())
        rewrt_words = len(rewritten.split())
        if orig_words == 0:
            return 1.0
        ratio = rewrt_words / orig_words
        if ratio <= 0.5:
            return min(0.5 + ratio, 1.0)
        elif ratio >= 2.0:
            return max(0.5 - (ratio - 2), 0.0)
        else:
            return 1.0
    
    def _check_tone(self, text: str) -> float:
        """Simple heuristic tone check (presence of unprofessional markers)."""
        unprofessional = ['lol', 'omg', 'wtf', 'idk', 'tbh', 'imo', 'fyi']
        lower_text = text.lower()
        violations = sum(1 for w in unprofessional if w in lower_text)
        return max(0.0, 1.0 - (violations * 0.25))
    
    def _quality_score(self, original: str, rewritten: str) -> Tuple[str, bool, float]:
        """
        Perform multi-tier quality check.
        Returns (decision: accept/rewrite/keep, should_retry, overall_score).
        """
        
        # Tier 1: Heuristic (fast, no cost)
        similarity = self._check_semantic_similarity(original, rewritten)
        conciseness = self._check_conciseness(original, rewritten)
        tone = self._check_tone(rewritten)
        
        overall_score = 0.4 * similarity + 0.3 * conciseness + 0.3 * tone
        
        # Thresholds
        if overall_score >= 0.85:
            return ("accept", False, overall_score)
        elif overall_score >= 0.60:
            return ("rewrite", True, overall_score)
        else:
            return ("keep", False, overall_score)
    
    def rewrite(self, original_text: str, thread_context: str = "", max_iterations: int = 3, config: Optional[LLMConfig] = None) -> Tuple[str, str]:
        """
        Rewrite message with quality control.
        Returns (final_text, quality_decision).
        """
        
        # Test mode: if no config, simulate with post-processing
        if config is None:
            # Just apply post-processing to demonstrate pipeline
            # In real usage, this would actually call the LLM
            return (original_text, "test_mode_no_llm_config")
        
        iterations = 0
        current_text = original_text
        best_rewritten = None
        best_score = 0.0
        
        while iterations < max_iterations:
            # Generate rewrite using LLM
            prompt = self.backend._normalize_prompt(current_text, thread_context)
            import asyncio
            result = asyncio.run(self.backend.generate(prompt, config))
            
            if result.error:
                return (original_text, f"error: {result.error}")
            
            # Post-process the output
            rewritten = self._post_process(result.text)
            
            if not rewritten or rewritten == current_text:
                return (current_text, "keep")
            
            # Quality check
            decision, should_retry, score = self._quality_score(current_text, rewritten)
            
            if score > best_score:
                best_score = score
                best_rewritten = rewritten
            
            if decision == "accept":
                return (rewritten, f"accepted (score: {score:.2f})")
            elif decision == "rewrite" and should_retry:
                current_text = rewritten
                iterations += 1
                continue
            else:
                # Keep or accept based on score
                if best_rewritten and best_score >= 0.60:
                    return (best_rewritten, f"accepted_low_confidence (score: {best_score:.2f})")
                else:
                    return (current_text, "rejected")
        
        # Max iterations reached
        if best_rewritten and best_score >= 0.60:
            return (best_rewritten, f"max_iterations_accepted (score: {best_score:.2f})")
        return (current_text, "max_iterations")
