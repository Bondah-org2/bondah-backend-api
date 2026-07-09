# Leveling System
PROGRESSION_CONFIG = {
    'phases': [
        {'max_level': 20, 'matches_per_level': 500},
        {'max_level': 59, 'matches_per_level': 800},
        {'max_level': float('inf'), 'matches_per_level': 1000},
    ],
    'badges': [
        {'title': 'Uprising', 'min_level': 0, 'max_level': 9},
        {'title': 'Connector', 'min_level': 10, 'max_level': 24},
        {'title': 'Expert', 'min_level': 25, 'max_level': 44},
        {'title': 'Professional', 'min_level': 45, 'max_level': 59},
        {'title': 'Principal', 'min_level': 60, 'max_level': float('inf')},
    ]
}