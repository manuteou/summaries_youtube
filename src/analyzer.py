"""
Analyzer module for SynthetIA - Comparison and fact extraction.
Uses LLM for intelligent analysis of syntheses.
"""
import re
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher, unified_diff


@dataclass
class ExtractedFact:
    """Represents an extracted fact from a synthesis."""
    fact_type: str  # "date", "number", "name", "location", "quote"
    value: str
    context: str
    source: Optional[str] = None


@dataclass
class Contradiction:
    """Represents a detected contradiction between sources."""
    topic: str
    statement_1: str
    source_1: str
    statement_2: str
    source_2: str
    severity: str  # "low", "medium", "high"


class Analyzer:
    """Analysis tools for syntheses comparison and fact extraction."""
    
    def __init__(self, llm_client=None, model: str = None):
        """
        Initialize analyzer.
        
        Args:
            llm_client: Ollama client for LLM-based analysis (optional)
            model: Model name for LLM queries (optional)
        """
        self.client = llm_client
        self.model = model
    
    # --- Text Comparison ---
    
    def compare_texts(self, text1: str, text2: str) -> Dict[str, Any]:
        """
        Compare two texts and return similarity metrics and differences.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Dictionary with similarity ratio and differences
        """
        # Clean texts for comparison
        clean1 = self._clean_for_comparison(text1)
        clean2 = self._clean_for_comparison(text2)
        
        # Calculate similarity
        matcher = SequenceMatcher(None, clean1, clean2)
        similarity = matcher.ratio()
        
        # Get diff blocks
        diff_lines = list(unified_diff(
            clean1.split('\n'),
            clean2.split('\n'),
            lineterm='',
            fromfile='Synthèse 1',
            tofile='Synthèse 2'
        ))
        
        # Identify unique parts
        unique_to_1 = []
        unique_to_2 = []
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'delete':
                unique_to_1.append(clean1[i1:i2])
            elif tag == 'insert':
                unique_to_2.append(clean2[j1:j2])
        
        return {
            "similarity": round(similarity * 100, 1),
            "diff_lines": diff_lines,
            "unique_to_1": unique_to_1[:10],  # Limit for display
            "unique_to_2": unique_to_2[:10],
            "matching_blocks": len(matcher.get_matching_blocks()) - 1
        }
    
    def _clean_for_comparison(self, text: str) -> str:
        """Remove HTML tags and normalize whitespace."""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    # --- Fact Extraction ---
    
    def extract_facts_regex(self, text: str) -> List[ExtractedFact]:
        """
        Extract facts using regex patterns (fast, no LLM needed).
        
        Args:
            text: Text to analyze
            
        Returns:
            List of extracted facts
        """
        facts = []
        clean_text = self._clean_for_comparison(text)
        
        # Date patterns (French and international)
        date_patterns = [
            r'\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b',  # DD/MM/YYYY
            r'\b(\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4})\b',
            r'\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})\b',
            r'\b(\d{4})\b',  # Year alone
        ]
        
        for pattern in date_patterns:
            for match in re.finditer(pattern, clean_text, re.IGNORECASE):
                # Get context (50 chars before and after)
                start = max(0, match.start() - 50)
                end = min(len(clean_text), match.end() + 50)
                context = clean_text[start:end]
                
                facts.append(ExtractedFact(
                    fact_type="date",
                    value=match.group(1),
                    context=f"...{context}..."
                ))
        
        # Number patterns (with units)
        number_patterns = [
            r'(\d+(?:[,\.]\d+)?(?:\s*(?:millions?|milliards?|%|€|\$|USD|EUR|km|m²|tonnes?|kg)))',
            r'(\d+(?:\s*\d+)*(?:[,\.]\d+)?)\s*(?:euros?|dollars?|personnes?|habitants?|employés?)',
        ]
        
        for pattern in number_patterns:
            for match in re.finditer(pattern, clean_text, re.IGNORECASE):
                start = max(0, match.start() - 50)
                end = min(len(clean_text), match.end() + 50)
                context = clean_text[start:end]
                
                facts.append(ExtractedFact(
                    fact_type="number",
                    value=match.group(0).strip(),
                    context=f"...{context}..."
                ))
        
        # Named entities (capitalized sequences)
        name_pattern = r'\b([A-Z][a-zéèêëàâäùûüôöîï]+(?:\s+[A-Z][a-zéèêëàâäùûüôöîï]+)+)\b'
        for match in re.finditer(name_pattern, clean_text):
            # Filter out common words that start sentences
            if match.group(1).split()[0].lower() not in ['la', 'le', 'les', 'un', 'une', 'des', 'ce', 'cette']:
                start = max(0, match.start() - 30)
                end = min(len(clean_text), match.end() + 30)
                context = clean_text[start:end]
                
                facts.append(ExtractedFact(
                    fact_type="name",
                    value=match.group(1),
                    context=f"...{context}..."
                ))
        
        # Remove duplicates
        seen = set()
        unique_facts = []
        for fact in facts:
            key = (fact.fact_type, fact.value)
            if key not in seen:
                seen.add(key)
                unique_facts.append(fact)
        
        return unique_facts[:50]  # Limit results
    
    def extract_facts_llm(self, text: str) -> List[ExtractedFact]:
        """
        Extract facts using LLM (more accurate but slower).
        
        Args:
            text: Text to analyze
            
        Returns:
            List of extracted facts
        """
        if not self.client or not self.model:
            return self.extract_facts_regex(text)
        
        prompt = f"""Analyse le texte suivant et extrais les faits importants.
        
Pour chaque fait, indique:
- type: "date", "number", "name", "location", ou "quote"
- value: la valeur exacte
- context: une courte phrase de contexte

Réponds en JSON avec cette structure:
{{"facts": [{{"type": "...", "value": "...", "context": "..."}}]}}

Texte:
{text[:3000]}

JSON:"""
        
        try:
            response = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response['message']['content']
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return [
                    ExtractedFact(
                        fact_type=f.get('type', 'unknown'),
                        value=f.get('value', ''),
                        context=f.get('context', '')
                    )
                    for f in data.get('facts', [])
                ]
        except Exception as e:
            print(f"LLM fact extraction error: {e}")
        
        # Fallback to regex
        return self.extract_facts_regex(text)
    
    # --- Contradiction Detection ---
    
    def detect_contradictions_regex(self, texts: List[Tuple[str, str]]) -> List[Contradiction]:
        """
        Detect potential contradictions between multiple texts (heuristic approach).
        
        Args:
            texts: List of (text, source_name) tuples
            
        Returns:
            List of potential contradictions
        """
        contradictions = []
        
        # Extract numbers with context from all texts
        number_contexts = []
        for text, source in texts:
            clean = self._clean_for_comparison(text)
            # Find numbers with surrounding context
            for match in re.finditer(r'(\d+(?:[,\.]\d+)?(?:\s*(?:%|millions?|milliards?))?)([^.]*\.)', clean):
                number_contexts.append({
                    'number': match.group(1),
                    'context': match.group(2),
                    'source': source
                })
        
        # Compare numbers in similar contexts
        for i, ctx1 in enumerate(number_contexts):
            for ctx2 in number_contexts[i+1:]:
                if ctx1['source'] != ctx2['source']:
                    # Check if contexts are similar but numbers differ
                    context_sim = SequenceMatcher(None, ctx1['context'], ctx2['context']).ratio()
                    if context_sim > 0.5 and ctx1['number'] != ctx2['number']:
                        contradictions.append(Contradiction(
                            topic="Données chiffrées",
                            statement_1=f"{ctx1['number']}: {ctx1['context'][:100]}",
                            source_1=ctx1['source'],
                            statement_2=f"{ctx2['number']}: {ctx2['context'][:100]}",
                            source_2=ctx2['source'],
                            severity="medium"
                        ))
        
        return contradictions[:10]  # Limit results
    
    def detect_contradictions_llm(self, texts: List[Tuple[str, str]]) -> List[Contradiction]:
        """
        Detect contradictions using LLM (more accurate).
        
        Args:
            texts: List of (text, source_name) tuples
            
        Returns:
            List of contradictions
        """
        if not self.client or not self.model or len(texts) < 2:
            return self.detect_contradictions_regex(texts)
        
        # Prepare texts for analysis
        combined = "\n\n---\n\n".join([
            f"SOURCE: {source}\n{text[:1500]}"
            for text, source in texts[:3]  # Limit to 3 sources
        ])
        
        prompt = f"""Compare les sources suivantes et identifie les contradictions ou incohérences.

{combined}

Pour chaque contradiction trouvée, indique:
- topic: le sujet de la contradiction
- statement_1: l'affirmation de la source 1
- source_1: nom de la source
- statement_2: l'affirmation contradictoire
- source_2: nom de la source
- severity: "low", "medium", ou "high"

Réponds en JSON: {{"contradictions": [...]}}

JSON:"""
        
        try:
            response = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response['message']['content']
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return [
                    Contradiction(**c)
                    for c in data.get('contradictions', [])
                ]
        except Exception as e:
            print(f"LLM contradiction detection error: {e}")
        
        return self.detect_contradictions_regex(texts)
    
    # --- Summary Statistics ---
    
    def get_text_stats(self, text: str) -> Dict[str, Any]:
        """Get basic statistics about a text."""
        clean = self._clean_for_comparison(text)
        words = clean.split()
        sentences = re.split(r'[.!?]+', clean)
        
        return {
            "word_count": len(words),
            "sentence_count": len([s for s in sentences if s.strip()]),
            "char_count": len(clean),
            "avg_word_length": sum(len(w) for w in words) / max(1, len(words)),
            "avg_sentence_length": len(words) / max(1, len(sentences))
        }


# Singleton
_analyzer_instance = None

def get_analyzer(llm_client=None, model=None) -> Analyzer:
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = Analyzer(llm_client, model)
    return _analyzer_instance
