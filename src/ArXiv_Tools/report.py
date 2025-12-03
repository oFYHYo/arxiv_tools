import os
from datetime import datetime, timedelta
from copy import deepcopy
from .arxiv_index_fetch import query_arxiv_dict,query_arxiv_catchup_dict
from .zotero_query import zotero_query
from .codex import replace_characters, quant_ph
from . import arxiv_logger

logger = arxiv_logger

def _get_arxiv_doi(arxiv_id):
    arxiv_doi = arxiv_id.replace(':', '.')
    arxiv_doi = f'10.48550/{arxiv_doi}'
    return arxiv_doi

def _get_arxiv_url(arxiv_id):
    root_url = 'https://arxiv.org/abs'
    arg = arxiv_id.replace('arXiv:', '/')
    arxiv_url = f'{root_url}{arg}'
    return arxiv_url

def _generate_ai_summary(title, abstract, provider='gemini'):
    """Generate AI summary using specified provider"""

    prompt = f"""Summarize this arXiv physics paper (chem-ph / quant-ph) in 2–3 concise sentences, focusing on:
                1. The central scientific problem and the main contribution of the work.
                2. The core theoretical framework, computational method, or experimental approach used.
                3. The relevance or potential impact for electronic structure theory, quantum chemistry, condensed matter physics, or quantum information.

                Title: {title}

                Abstract: {abstract}

                Translate English to Chinese and output only the Chinese text. Provide only the translated summary, no preamble, no commentary, no additional text.
                """
    
    prompt_title = f'''Based on the scientific context inferred from the title and abstract below, translate the article's title into accurate and domain-appropriate Chinese, ensuring correct usage of physics, quantum chemistry, and quantum information terminology.

                    Title: {title}

                    Abstract: {abstract}

                    Provide only the translated title, no preamble, no explanation, no additional text.
                    '''
    
    if provider == 'claude':
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
        except Exception as e:
            logger.warning(f"Failed to generate Claude summary: {e}")
            return None
            
    elif provider == 'openai':
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

            response = client.chat.completions.create(
                model="gpt-4o",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning(f"Failed to generate OpenAI summary: {e}")
            return None
            
    elif provider == 'gemini':
        try:
            import google.generativeai as genai
            genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
            summary_model = 'gemini-2.5-pro'
            translation_model = 'gemini-2.5-flash'
            summary_config = genai.GenerationConfig(
            temperature=0.2,        # 低温，保证事实准确，但允许少量语言润色
            top_p=0.95,             # 保持默认或稍高，确保覆盖主要逻辑
            top_k=40,
            # max_output_tokens=8192, # 给予充足的输出空间
        )
            
            translation_config = genai.GenerationConfig(
            temperature=0.1,       # 接近 0，追求确定性和术语的精准对应
            top_p=1.0,             # 不进行截断，考虑所有可能性中最优的
            # max_output_tokens=256, # 标题通常很短，限制长度防止废话
        )

            model = genai.GenerativeModel(summary_model,generation_config=summary_config)
            
            response = model.generate_content(prompt)

            model_title = genai.GenerativeModel(translation_model,generation_config=translation_config)
            response_title = model_title.generate_content(prompt_title)

            return response.text, response_title.text
        except Exception as e:
            logger.warning(f"Failed to generate Gemini summary: {e}")
            return None
    else:
        logger.warning(f"Unknown AI provider: {provider}")
        return None

def _gen_arxiv_markdown(arxiv_id, title, authors, abstract, include_ai_summary=False, ai_provider='gemini'):
    arxiv_link_text = '[' + arxiv_id+ ']' + '(' + _get_arxiv_url(arxiv_id) + ')'
    title_text = title
    author_text = ''
    for author in authors:
        author_text += f'{author}, '
    abstract_text = abstract
    for key in replace_characters:
        abstract_text = abstract_text.replace(key, replace_characters[key])
    
    # Generate AI summary if requested
    ai_summary_section = ''
    title_translate = ''
    if include_ai_summary:
        ai_summary, ai_title = _generate_ai_summary(title, abstract, ai_provider)
        if ai_summary:
            title_translate = f'''Title:  {ai_title}'''
            ai_summary_section = f'''
> [!quote]- AI Summary ({ai_provider}):
> {ai_summary}

'''
            
    
    arxiv_markdown = f'''
### {arxiv_id}

Links:

- [ ] {arxiv_link_text} 

Title:  {title_text}

{title_translate}

Authors:  {author_text}
{ai_summary_section}

> [!quote]- Abstract
> {abstract_text}


'''
    
    return arxiv_markdown


def _gen_data(arxiv_dict, Zot_=None, include_ai_summary=False, ai_provider='gemini'):
    collect_dict = {}
    not_collect_dict = {}
    
    for _, (arxiv_id, (title, authors, abstract, external_)) in enumerate(arxiv_dict.items()):
        arxiv_doi = _get_arxiv_doi(arxiv_id)
        try:
            query_res = Zot_.query_('DOI', arxiv_doi)
        except:
            query_res = []
        
        markdown_content = _gen_arxiv_markdown(
            arxiv_id, title, authors, abstract, include_ai_summary, ai_provider
        )
        
        if query_res.__len__():
            last_ok = query_res
            collect_dict[arxiv_id] = markdown_content
        else:
            if external_.__len__() == 2:
                external_doi = external_[0]
                try:
                    query_res = Zot_.query_('DOI', external_doi)
                except:
                    query_res = []
                if query_res.__len__():
                    last_ok = query_res
                    collect_dict[arxiv_id] = markdown_content
                else:
                    not_collect_dict[arxiv_id] = markdown_content
            else:
                not_collect_dict[arxiv_id] = markdown_content
    return collect_dict, not_collect_dict


def _gen_oneday_markdown(date_string, oneday_arxiv_dict, Zot_, old_data=None, include_ai_summary=False, ai_provider='gemini'):

    oneday_arxiv_dict = deepcopy(oneday_arxiv_dict)
    category = oneday_arxiv_dict['category']
    del oneday_arxiv_dict['category']
    collect_dict, not_collect_dict = _gen_data(oneday_arxiv_dict, Zot_, include_ai_summary, ai_provider)

    new_data = []
    date_markdown = f'# {date_string} preprint by arxiv_tools\n\nThere are a total of {oneday_arxiv_dict.__len__()} articles today.\n\n'
    date_markdown +=  f'''
---
tags:
  - #{category}-{date_string}
---


```dataview
TASK
from #{category}-{date_string}

WHERE completed

```

'''
    date_markdown += '## collected\n\n'
    for key in sorted([key for key in collect_dict]):
        value = collect_dict[key]
        date_markdown += value
        if old_data is not None:
            if key not in old_data:
                new_data.append(key)

    date_markdown += '## not collected\n\n'

    for key in sorted([key for key in not_collect_dict]):
        value = not_collect_dict[key]
        date_markdown += value
        if old_data is not None:
            if key not in old_data:
                new_data.append(key)
            
    if new_data.__len__(): 
        date_markdown += '## update \n\n'

        for key in sorted([key for key in new_data]):
            value = f'- [ ] [[#{key}]]\n'
            date_markdown += value
        
    return date_markdown

def parse_old_report(file_path):
    if os.path.exists(file_path):
        
        with open(
                file_path, 
                "r", encoding="utf-8"
            ) as f:
            lines = f.readlines()
        old_title_lines = []
        for line in lines:
            if line.startswith('### arXiv:'):
                arxiv_id_str = line[4:-1].strip()
                old_title_lines.append(arxiv_id_str)
            if line.startswith('- [x]'):
                arxiv_id_str = line[8:-2].strip()
                old_title_lines.append(arxiv_id_str)
            
        return old_title_lines
    else:
        return None
        
def filter_arxiv_to_md(year: int, month: int, md_folder: str, query_args: dict=quant_ph, 
                       category='quant-ph', include_ai_summary=False, ai_provider='gemini', specific_day=None, use_url='catchup'):
    """
    Fetch arXiv papers and generate markdown reports
    
    Args:
        year: Year to fetch
        month: Month to fetch
        md_folder: Folder to save markdown files
        query_args: Query arguments for arXiv API
        category: ArXiv category
        include_ai_summary: Whether to generate AI summaries
        ai_provider: AI provider to use (claude/openai/gemini)
        specific_day: If set, only fetch this specific day (1-31). If None, fetch all days in month
    """
    try:
        Zot_ = zotero_query() # default local use
        Zot_.get_everything()
    except:
        Zot_ = None
    root_dir = md_folder
    
    # Determine which days to process
    if specific_day is not None:
        # Process only the specific day
        days_to_process = [specific_day]
    else:
        # Process all days in the month (1-31)
        days_to_process = range(1, 32)
    
    for day in days_to_process:
        date_from_date = f'{year}-{month:02}-{day:02}'
        
        if use_url == 'advance':
            d = datetime.strptime(date_from_date, "%Y-%m-%d")
            date_to_date = (d + timedelta(days=1)).strftime("%Y-%m-%d")
            arxiv_dict = query_arxiv_dict(date_from_date, date_to_date, query_args) # Use advance search url

        elif use_url == 'catchup':
            arxiv_dict = query_arxiv_catchup_dict(date=date_from_date, query_args=query_args) # Use catchup url
        
        if arxiv_dict.__len__():
            arxiv_dict['category'] = category
            # print(arxiv_dict)
            logger.info(f'{arxiv_dict.__len__() - 1}')
            year_dir = os.path.join(root_dir, f'{year}')
            month_dir = os.path.join(year_dir, f'{month:02}')
            os.makedirs(month_dir, exist_ok=True)
            date_string = f'{year}-{month:02}-{day:02}'
            logger.info(f'Processing {date_from_date}, total num: {arxiv_dict.__len__()} -1 ')
            oneday_report_file = os.path.join(month_dir, f'{day:02}.md')
            parse_old = parse_old_report(oneday_report_file)
            
            markdown_str = _gen_oneday_markdown(
                date_string, arxiv_dict, Zot_, parse_old, include_ai_summary, ai_provider
            )
            
            with open(
                oneday_report_file, 
                "w", encoding="utf-8"
            ) as f:
                f.write(markdown_str)
        else:
            # Only log if we're processing a specific day (avoid spam for whole month)
            if specific_day is not None:
                logger.info(f'No papers found for {date_from_date}')