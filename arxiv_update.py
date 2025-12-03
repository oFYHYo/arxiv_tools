import time
import os
import argparse
import logging
from ArXiv_Tools import arxiv_logger
from ArXiv_Tools.report import filter_arxiv_to_md
from ArXiv_Tools.codex import query_args

logger = arxiv_logger

def parse_time_argument(time_str):
    """
    Parse time argument and return list of (year, month, day) tuples
    
    Supports:
    - '1949.10' or 'default' -> current month (all days)
    - '2025.11' -> all days in November 2025
    - '2025.11.10' -> single day (November 10, 2025)
    - '2025.11.10,2025.11.15' -> multiple specific days
    """
    results = []
    
    for time_part in time_str.split(','):
        time_part = time_part.strip()
        
        # Default case - current month
        if time_part == '1949.10' or time_part == 'default':
            localtime = time.localtime()
            year = int(localtime.tm_year)
            month = int(localtime.tm_mon)
            results.append((year, month, None))  # None means all days in month
        
        else:
            parts = time_part.split('.')
            
            if len(parts) == 2:
                # Format: YYYY.MM - all days in month
                year = int(parts[0])
                month = int(parts[1])
                results.append((year, month, None))
            
            elif len(parts) == 3:
                # Format: YYYY.MM.DD - specific day
                year = int(parts[0])
                month = int(parts[1])
                day = int(parts[2])
                results.append((year, month, day))
            
            else:
                logger.error(f"Invalid time format: {time_part}")
                raise ValueError(f"Time format must be YYYY.MM or YYYY.MM.DD, got: {time_part}")
    
    return results

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='ArXiv paper fetcher with AI summaries',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Time format examples:
  --time 2025.11           Fetch all days in November 2025
  --time 2025.11.10        Fetch only November 10, 2025
  --time 2025.11.10,2025.11.15   Fetch specific days
  --time 1949.10           Fetch current month (default)
        """
    )
    parser.add_argument("--time", default='1949.10', 
                        help="Time to query: YYYY.MM (month) or YYYY.MM.DD (specific day)", type=str)
    parser.add_argument("--arxiv_folder", default='/home/ansatz/data/obsidian/1/arxiv_datas/', 
                        help="Place to store arxiv data", type=str)
    parser.add_argument("--categroy", default='quant-ph', 
                        help="Category of arxiv papers (comma-separated for multiple)", type=str)
    parser.add_argument("--ai_summary", action='store_true', 
                        help="Generate AI summaries for papers")
    parser.add_argument("--ai_provider", default='claude', choices=['claude', 'openai', 'gemini'],
                        help="AI provider for summaries (claude/openai/gemini)")
    parser.add_argument("--use_url", default='catchup', choices=['advance', 'catchup'],
                        help='''URL type for fetching arXiv data. 

                            advance:  https://arxiv.org/search/advanced
                            catchup:  https://arxiv.org/catchup ''')

    args = parser.parse_args() 
    arxiv_folder = args.arxiv_folder
    categroy = args.categroy
    time_ = args.time
    ai_summary = args.ai_summary
    ai_provider = args.ai_provider
    use_url = args.use_url
    
    # Display settings
    logger.info(f"AI Summary: {'Enabled' if ai_summary else 'Disabled'}")
    if ai_summary:
        logger.info(f"AI Provider: {ai_provider}")
    
    # Parse time argument
    try:
        time_specs = parse_time_argument(time_)
    except ValueError as e:
        logger.error(str(e))
        exit(1)
    
    for cat_ in categroy.split(','):
        md_folder = os.path.join(arxiv_folder, cat_)
        try:
            _query_args = query_args[cat_]
        except:
            logger.error(f'Category: {cat_} not supported, create issue to remind author')
            raise RuntimeError
        
        for year, month, day in time_specs:
            if day is None:
                # Process entire month
                logger.info(f'Script is running to fetch {cat_} {year}.{month:02} (all days)')
                filter_arxiv_to_md(
                    year=year,
                    month=month,
                    md_folder=md_folder,
                    query_args=_query_args,
                    category=cat_,
                    include_ai_summary=ai_summary,
                    ai_provider=ai_provider,
                    specific_day=None,
                    use_url=use_url
                )
            else:
                # Process specific day
                logger.info(f'Script is running to fetch {cat_} {year}.{month:02}.{day:02} (single day)')
                filter_arxiv_to_md(
                    year=year,
                    month=month,
                    md_folder=md_folder,
                    query_args=_query_args,
                    category=cat_,
                    include_ai_summary=ai_summary,
                    ai_provider=ai_provider,
                    specific_day=day,
                    use_url=use_url
                )