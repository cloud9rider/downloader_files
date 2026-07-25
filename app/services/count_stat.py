from collections import Counter
from typing import List, Tuple, Dict
from pathlib import Path
import aiofiles

async def calculate_stat(file_names: List[str]) -> Tuple[Dict[str, int], Dict[str, Dict[str, int]]]:
    total_stats = {str(digit): 0 for digit in range(10)}
    per_file_stats = {}
    
    for file_name in file_names:
        file_path = Path("files") / file_name
        
        if not file_path.exists():
            continue
        
        async with aiofiles.open(file_path, 'r') as file:
            content = await file.read()
            content = content.strip()
        
        counter = Counter(content)
        
        file_stats = {str(digit): counter.get(str(digit), 0) for digit in range(10)}
        
        for digit in range(10):
            total_stats[str(digit)] += file_stats[str(digit)]
        
        per_file_stats[file_name] = file_stats
    
    return total_stats, per_file_stats