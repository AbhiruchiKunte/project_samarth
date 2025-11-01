import re
from typing import Dict, List
from modules.utils import parse_column_name

class NLUEngine:
    """Natural Language Understanding for query parsing"""
    
    def __init__(self, data_loader):
        self.data_loader = data_loader
        self.states = data_loader.get_available_states()
        self.crops = [c.lower() for c in data_loader.get_available_crops()]
        self.years = data_loader.get_available_years()
    
    def parse_query(self, query: str) -> Dict:
        """Parse natural language query and extract entities"""
        query_lower = query.lower()
        
        result = {
            'type': self._identify_query_type(query_lower),
            'states': self._extract_states(query_lower),
            'crops': self._extract_crops(query_lower),
            'years': self._extract_years(query_lower),
            'limit': self._extract_limit(query_lower),
            'comparison': any(word in query_lower for word in ['vs', 'versus', 'compare', 'comparison']),
            'correlation': any(word in query_lower for word in ['correlat', 'relationship', 'impact', 'affect']),
            'original_query': query
        }
        
        return result
    
    def _identify_query_type(self, query: str) -> str:
        """Identify the type of query"""
        patterns = {
            'trend': ['trend', 'over time', 'decade', 'years', 'historical', 'change'],
            'comparison': ['compare', 'vs', 'versus', 'difference', 'between'],
            'ranking_high': ['top', 'highest', 'maximum', 'largest', 'most', 'best'],
            'ranking_low': ['lowest', 'minimum', 'smallest', 'least', 'worst', 'bottom'],
            'correlation': ['correlat', 'relationship', 'impact', 'affect', 'influence', 'link'],
            'policy': ['policy', 'recommend', 'suggest', 'should', 'argument', 'promote']
        }
        
        for query_type, keywords in patterns.items():
            if any(keyword in query for keyword in keywords):
                return query_type
        
        return 'general'
    
    def _extract_states(self, query: str) -> List[str]:
        """Extract state names from query"""
        found_states = []
        
        # Direct state name matching
        for state in self.states:
            if state.lower() in query:
                found_states.append(state)
        
        # Handle common abbreviations
        abbrev_map = {
            'up': 'Uttar Pradesh',
            'mp': 'Madhya Pradesh',
            'hp': 'Himachal Pradesh',
            'wb': 'West Bengal',
            'tn': 'Tamil Nadu',
            'ap': 'Andhra Pradesh'
        }
        
        for abbrev, full_name in abbrev_map.items():
            if f' {abbrev} ' in f' {query} ' or f' {abbrev},' in query:
                if full_name not in found_states:
                    found_states.append(full_name)
        
        return found_states
    
    def _extract_crops(self, query: str) -> List[str]:
        """Extract crop names from query"""
        found_crops = []
        
        for crop in self.crops:
            if crop in query:
                found_crops.append(crop)
        
        # Handle plural forms
        crop_variants = {
            'crops': self.crops,
            'grains': ['rice', 'wheat', 'jowar', 'bajra', 'maize'],
            'pulses': ['gram', 'tur', 'urad', 'moong'],
            'oilseeds': ['groundnut', 'sesamum', 'rapeseed', 'linseed', 'castorseed']
        }
        
        for variant, crop_list in crop_variants.items():
            if variant in query and not found_crops:
                return crop_list[:5]  # Return top 5 from category
        
        return found_crops
    
    def _extract_years(self, query: str) -> List[str]:
        """Extract year mentions from query"""
        # Extract explicit years
        years = re.findall(r'\b(20\d{2}|19\d{2})\b', query)
        
        # Handle relative time expressions
        if 'last' in query:
            num_match = re.search(r'last\s+(\d+)\s+years?', query)
            if num_match:
                n_years = int(num_match.group(1))
                if self.years:
                    latest_year = int(self.years[-1])
                    years = [str(y) for y in range(latest_year - n_years + 1, latest_year + 1)]
        
        return years
    
    def _extract_limit(self, query: str) -> int:
        """Extract numeric limits (e.g., 'top 5')"""
        patterns = [
            r'\b(?:top|first|last|bottom)\s+(\d+)\b',
            r'\b(\d+)\s+(?:top|crops|states)\b'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                return int(match.group(1))
        
        return 5  # Default limit
