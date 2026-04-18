"""
SALTS AI Search - Natural Language Movie & TV Show Discovery
Uses OpenAI API via Emergent proxy (https://integrations.emergentagent.com/llm)
Native urllib for Kodi 21+ compatibility.
"""
import json
import ssl
import xbmc
import xbmcaddon
from urllib.request import urlopen, Request
from urllib.error import HTTPError

ADDON = xbmcaddon.Addon()
SSL_CTX = ssl._create_unverified_context()

AI_MODELS = ['gpt-4o-mini', 'gpt-4o', 'gpt-5.2']

# Emergent proxy endpoint (works with Emergent universal key)
API_ENDPOINT = 'https://integrations.emergentagent.com/llm/v1/chat/completions'

SYSTEM_PROMPT = """You are a movie and TV show recommendation engine. The user will describe what they want to watch using natural language. You MUST respond with ONLY a valid JSON array of recommendations.

Each item must have:
- "title": exact movie or show title
- "year": release year (integer)
- "type": "movie" or "tv"
- "reason": one sentence explaining why it matches (max 15 words)

Return 10-15 results. Prioritize well-known titles. Only return the JSON array, no markdown, no explanation.

Example response:
[{"title": "Interstellar", "year": 2014, "type": "movie", "reason": "Epic time dilation and wormhole sci-fi"}, {"title": "Primer", "year": 2004, "type": "movie", "reason": "Mind-bending low-budget time travel thriller"}]"""


def ai_search(query, media_filter='all'):
 """Send natural language query to OpenAI via Emergent proxy, return list of recommendations.
 
 Args:
 query: Natural language search query
 media_filter: 'all', 'movie', or 'tv'
 
 Returns:
 list of dicts with title, year, type, reason
 """
 api_key = ADDON.getSetting('ai_api_key')
 if not api_key:
 return []
 
 model_idx = int(ADDON.getSetting('ai_model') or 0)
 model = AI_MODELS[model_idx] if model_idx < len(AI_MODELS) else 'gpt-4o-mini'
 
 # Add media filter to query
 user_msg = query
 if media_filter == 'movie':
 user_msg += '\n\nOnly recommend movies, no TV shows.'
 elif media_filter == 'tv':
 user_msg += '\n\nOnly recommend TV shows, no movies.'
 
 payload = {
 'model': model,
 'messages': [
 {'role': 'system', 'content': SYSTEM_PROMPT},
 {'role': 'user', 'content': user_msg}
 ],
 'temperature': 0.7,
 'max_tokens': 2000
 }
 
 try:
 data = json.dumps(payload).encode('utf-8')
 req = Request(
 API_ENDPOINT,
 data=data,
 headers={
 'Content-Type': 'application/json',
 'Authorization': f'Bearer {api_key}',
 'User-Agent': 'SALTS/2.4'
 },
 method='POST'
 )
 
 with urlopen(req, context=SSL_CTX, timeout=30) as resp:
 result = json.loads(resp.read().decode('utf-8'))
 
 content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
 
 # Parse JSON from response (handle markdown fences)
 content = content.strip()
 if content.startswith('```'):
 content = content.split('\n', 1)[-1].rsplit('```', 1)[0]
 
 recommendations = json.loads(content)
 
 if isinstance(recommendations, list):
 return recommendations
 
 return []
 
 except HTTPError as e:
 error_body = e.read().decode('utf-8', errors='replace')
 xbmc.log(f'AI Search HTTP error {e.code}: {error_body[:200]}', xbmc.LOGERROR)
 return []
 except json.JSONDecodeError as e:
 xbmc.log(f'AI Search JSON parse error: {e}', xbmc.LOGERROR)
 return []
 except Exception as e:
 xbmc.log(f'AI Search error: {e}', xbmc.LOGERROR)
 return []
