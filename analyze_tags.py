import os
import re
from github import Github
from subprocess import check_output

def get_tags_from_file(content):
    # Znajduje wszystkie tagi w sekcji właściwości pliku
    tags = set()
    properties_match = re.search(r'---\n([\s\S]*?)\n---', content)
    if properties_match:
        properties_content = properties_match.group(1)
        # Najpierw znajdź sekcję tags
        tags_section = re.search(r'tags:\s*\n((?:\s*-[^\n]*\n?)+)', properties_content)
        if tags_section:
            # Następnie wyodrębnij poszczególne tagi
            tags = set(
                tag.strip() 
                for tag in re.findall(r'-\s*([^\n]+)', tags_section.group(1))
            )
    return tags

def get_file_content(sha, file_path):
    try:
        return check_output(['git', 'show', f'{sha}:{file_path}']).decode('utf-8')
    except:
        return ''

def compare_tags(before_sha, after_sha):
    tag_stats = {}
    
    # Znajdź wszystkie pliki .md
    md_files = check_output(['git', 'ls-tree', '-r', after_sha, '--name-only']).decode('utf-8').splitlines()
    md_files = [f for f in md_files if f.endswith('.md')]
    
    for file_path in md_files:
        before_content = get_file_content(before_sha, file_path)
        after_content = get_file_content(after_sha, file_path)
        
        before_tags = get_tags_from_file(before_content)
        after_tags = get_tags_from_file(after_content)
        
        # Zlicz tagi
        for tag in before_tags | after_tags:
            if tag not in tag_stats:
                tag_stats[tag] = {'before': 0, 'after': 0}
            
            if tag in before_tags:
                tag_stats[tag]['before'] += 1
            if tag in after_tags:
                tag_stats[tag]['after'] += 1
    
    return tag_stats

def generate_markdown_table(stats):
    lines = ['| Tag | Przed | Po | Zmiana |', '|------|---------|--------|---------|']
    
    for tag, counts in sorted(stats.items()):
        before = counts['before']
        after = counts['after']
        
        if after > before:
            change = '🔺'
        elif after < before:
            change = '🔻'
        else:
            change = '🔲'
        
        lines.append(f'| {tag} | {before} | {after} | {change} |')
    
    return '\n'.join(lines)

# Główna logika
g = Github(os.environ['GITHUB_TOKEN'])
repo = g.get_repo(os.environ['GITHUB_REPOSITORY'])

# Pobierz aktualny release
releases = list(repo.get_releases())
current_release = releases[0]

# Znajdź poprzedni release
previous_release = releases[1] if len(releases) > 1 else None

if previous_release:
    stats = compare_tags(previous_release.tag_name, current_release.tag_name)
    table = generate_markdown_table(stats)
    
    # Zaktualizuj opis release'u
    current_body = current_release.body or ''
    new_body = f"{current_body}\n\n## Zmiany w ilości tagów\n{table}"
    current_release.update_release(name=current_release.title, message=new_body)