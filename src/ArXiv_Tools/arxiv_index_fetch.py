import re
from urllib.parse import urlencode
import feedparser
from datetime import datetime
from bs4 import BeautifulSoup
# from . import arxiv_logger
# from .codex import quant_ph
from ArXiv_Tools import arxiv_logger
from ArXiv_Tools.codex import quant_ph,chem_ph
logger = arxiv_logger
sub = 'quant-ph'

search_url = 'https://arxiv.org/search/advanced?'

test_url = 'https://arxiv.org/search/advanced?advanced=&terms-0-term=&terms-0-operator=AND&terms-0-field=title&classification-physics=y&classification-physics_archives=quant-ph&classification-include_cross_list=include&date-filter_by=date_range&date-year=&date-from_date=2025-02-01&date-to_date=2025-02-02&date-date_type=submitted_date&abstracts=show&size=200&order=submitted_date'



def query_arxiv_dict(date_from_date='2025-02-01', date_to_date='2025-02-02', query_args=quant_ph):

    query_args['date-from_date'] = date_from_date
    query_args['date-to_date'] = date_to_date

    query_dict = {}

    url_args = re.sub(
            "%2B", "+", urlencode(query_args)
        )
    # print(url_args)

    url = search_url + url_args
    # print(url)
    logger.info(f'Querying ArXiv URL: {url}')
    results = feedparser.parse(url)

    summary_text = results['feed']['summary']

    so = BeautifulSoup(summary_text, 'lxml')


    find_results = so.find_all(class_='arxiv-result')

    tmp_res = []
    for res in find_results:
        aso = BeautifulSoup(res.__str__(), 'lxml')

        list_title = aso.find(class_='list-title')
        arxiv_id_text = list_title.find('a').text
        arxiv_id = arxiv_id_text # with or without v version 

        title = aso.find(class_='title')
        title = title.text.strip()

        _authors = aso.find(class_='authors')
        authors = []
        for s in _authors.find_all('a'):
            authors.append(s.text)

        abstract = aso.find(class_='abstract-full')
        abstract = abstract.text.strip() # with less

        tags = aso.find_all(class_='tag')
        external_doi = ''
        for tag in tags:
            if tag.find(class_='fa fa-external-link'):
                href_link = tag.find_next()['href']
                external_doi = tag.text.strip()

        if len(external_doi) > 0:
            query_dict[arxiv_id] = [title, authors, abstract, (external_doi, href_link) ]
        else:
            query_dict[arxiv_id] = [title, authors, abstract, () ]
        # tmp_res.append([arxiv_id, title, authors, abstract])

    return query_dict

import requests
catchup_url = 'https://arxiv.org/catchup/'

def query_arxiv_catchup(subject='physics.chem-ph', date='2025-12-02'):
    """
    Query arXiv catchup page for new submissions and cross-lists.
    
    Args:
        subject: arXiv subject code (e.g., 'physics.chem-ph', 'quant-ph')
        date: Date in format 'YYYY-MM-DD'
    
    Returns:
        dict: Dictionary with arxiv_id as key and [title, authors, abstract, doi_info] as value
    """
    catchup_url = f'https://arxiv.org/catchup/{subject}/{date}?abs=True'
    
    logger.info(f'Querying ArXiv Catchup URL: {catchup_url}')
    
    try:
        response = requests.get(catchup_url)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f'Failed to fetch URL: {e}')
        return {}
    
    soup = BeautifulSoup(response.text, 'html.parser')
    query_dict = {}
    
    # Find all article sections (dt/dd pairs)
    articles = soup.find_all('dt')
    
    for dt in articles:
        dd = dt.find_next_sibling('dd')
        if not dd:
            continue
        
        # Check if this is in New submissions or Cross submissions section
        # by checking the previous h3 heading
        prev_h3 = dt.find_previous('h3')
        if not prev_h3:
            continue
        
        section_title = prev_h3.text.strip()
        # Only process New submissions and Cross submissions
        if 'New submissions' not in section_title and 'Cross' not in section_title:
            continue
        
        # Extract arXiv ID
        arxiv_link = dt.find('a', href=re.compile(r'/abs/'))
        if not arxiv_link:
            continue
        arxiv_id = arxiv_link.text.strip()
        
        # Extract metadata from dd
        meta_div = dd.find('div', class_='meta')
        if not meta_div:
            continue
        
        # Extract title
        title_div = meta_div.find('div', class_='list-title')
        if title_div:
            # Remove the "Title:" descriptor
            title = title_div.get_text(separator=' ', strip=True)
            title = re.sub(r'^Title:\s*', '', title)
        else:
            title = ''
        
        # Extract authors
        authors_div = meta_div.find('div', class_='list-authors')
        authors = []
        if authors_div:
            author_links = authors_div.find_all('a')
            for link in author_links:
                author_name = link.text.strip()
                authors.append(author_name)
        
        # Extract abstract
        abstract_p = meta_div.find('p', class_='mathjax')
        if abstract_p:
            abstract = abstract_p.get_text(separator=' ', strip=True)
        else:
            abstract = ''
        
        # Extract DOI if present (note: catchup pages typically don't show DOI)
        # But we'll check for it in case
        doi_info = ()
        comments_div = meta_div.find('div', class_='list-comments')
        if comments_div:
            doi_link = comments_div.find('a', href=re.compile(r'doi\.org'))
            if doi_link:
                doi_text = doi_link.text.strip()
                doi_href = doi_link['href']
                doi_info = (doi_text, doi_href)
        
        # Store in dictionary
        query_dict[arxiv_id] = [title, authors, abstract, doi_info]
    
    logger.info(f'Found {len(query_dict)} articles in New submissions and Cross submissions')
    return query_dict


def query_arxiv_catchup_dict(date='2025-12-02', query_args=quant_ph):
    """
    Wrapper function to match the original API style.
    
    Args:
        date: Date in format 'YYYY-MM-DD'
        subject: arXiv subject code
    
    Returns:
        dict: Dictionary with arxiv_id as key and [title, authors, abstract, doi_info] as value
    """
    if query_args == quant_ph:
        subject = 'quant-ph'
    elif query_args == chem_ph:
        subject = 'physics.chem-ph'

    return query_arxiv_catchup(subject=subject, date=date)


if __name__ == '__main__':
    target_date = '2025-12-02' 
    archive_sub = 'chem-ph' 
    query_dict = query_arxiv_dict(date_from_date='2025-12-02', date_to_date='2025-12-03', query_args=chem_ph)
    print(query_dict)
    print(f"Found {len(query_dict)} papers for {archive_sub} on {target_date}.")

    
    # 调用新的 Catch-up 函数
    res = query_arxiv_catchup(date='2025-12-02', subject='physics.chem-ph')
    print(res)
    print(f"Found {len(res)} papers from Catch-up for {archive_sub} on {target_date}.")

