import urllib.request
import urllib.parse
import re
import json
import os
from typing import List
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from src.exercise_library import ExerciseLibraryItem, add_or_update_exercise

class SearchFlowResult(BaseModel):
    exercises: List[ExerciseLibraryItem] = Field(description="List of exercises found and fully classified")

def scrape_web_search(query: str) -> List[dict]:
    """
    Searches DuckDuckGo HTML and YouTube to retrieve top articles and exercise video tutorials.
    Returns a list of dictionaries with 'title', 'link', and 'snippet'.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    results = []
    
    # 1. Search DuckDuckGo HTML for guides and exercise databases
    try:
        encoded_query = urllib.parse.quote_plus(query + " exercise guide tutorial")
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8', errors='ignore')
            
            # Extract results
            result_blocks = re.findall(r'<div class="result__body">(.*?)</div>\s*</div>', html, re.DOTALL)
            for block in result_blocks[:5]:
                link_match = re.search(r'href="([^"]+)"', block)
                title_match = re.search(r'<a class="result__snippet"[^>]*>(.*?)</a>', block, re.DOTALL)
                
                link = ""
                title = ""
                snippet = ""
                
                if link_match:
                    href = link_match.group(1)
                    # Parse duckduckgo redirect link if present
                    if "uddg=" in href:
                        try:
                            redirect_parts = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                            if "uddg" in redirect_parts:
                                href = redirect_parts["uddg"][0]
                        except Exception:
                            pass
                    if "duckduckgo.com" not in href and href.startswith("http"):
                        link = href
                
                title_m = re.search(r'<a class="result__snippet"[^>]*>(.*?)</a>', block)
                if title_m:
                    title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip()
                    
                snippet_m = re.search(r'<a class="result__snippet"[^>]*>(.*?)</a>', block)
                if snippet_m:
                    snippet = re.sub(r'<[^>]+>', '', snippet_m.group(1)).strip()
                    
                if link:
                    results.append({
                        "title": title or "Exercise Article",
                        "link": link,
                        "snippet": snippet or "Exercise instructions and form cues."
                    })
    except Exception as e:
        print(f"DuckDuckGo search error: {e}")
        
    # 2. Search YouTube to find direct exercise video/demo links
    try:
        encoded_query = urllib.parse.quote_plus(query + " exercise form demo tutorial")
        url = f"https://www.youtube.com/results?search_query={encoded_query}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8', errors='ignore')
            video_ids = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', html)
            seen_ids = set()
            for vid in video_ids:
                if vid not in seen_ids:
                    seen_ids.add(vid)
                    results.append({
                        "title": f"{query.title()} Video Demonstration",
                        "link": f"https://www.youtube.com/watch?v={vid}",
                        "snippet": f"Watch the correct form and tutorial video on YouTube."
                    })
                if len(seen_ids) >= 5:
                    break
    except Exception as e:
        print(f"YouTube search error: {e}")
        
    return results

def run_browser_search_flow(user_query: str) -> List[ExerciseLibraryItem]:
    """
    Executes the Browser Search Flow:
    1. Scrapes web & video search results for the user query.
    2. Uses ChatGroq with structured output to analyze, extract, and fully classify exercises.
    3. Saves new exercises to the exercise library.
    4. Returns the newly classified exercises.
    """
    # 1. Scrape web
    print(f"Scraping web results for query: '{user_query}'...")
    web_results = scrape_web_search(user_query)
    
    # Format search results for LLM
    search_context = ""
    if web_results:
        for idx, r in enumerate(web_results):
            search_context += f"Result #{idx+1}:\nTitle: {r['title']}\nLink: {r['link']}\nSnippet: {r['snippet']}\n\n"
    else:
        search_context = "No direct web results found. Please use your internal knowledge base of premium trainings and exercises."
        
    # 2. Invoke LLM to extract and classify exercises
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1)
    llm_structured = llm.with_structured_output(SearchFlowResult)
    
    prompt = f"""You are the Advanced Web-Search & Exercise Classification Agent.
    
    The user triggered a search flow for trainings & exercises matching this search query:
    SEARCH QUERY: "{user_query}"
    
    Here is a collection of real web pages and video search results we retrieved for this query:
    ---
    {search_context}
    ---
    
    YOUR TASK:
    Analyze the retrieved search results or use your own extensive training database, identify the exercise(s) mentioned or relevant, and extract and classify them into standard ExerciseLibraryItem schemas.
    
    CLASSIFICATION RULES:
    1. Identify the full and clear 'name' of the exercise (e.g. "Dumbbell Incline Bench Press").
    2. Generate a unique snake_case 'id' (e.g. "dumbbell_incline_bench_press").
    3. Generate a clear and descriptive 'description' explaining the correct exercise execution.
    4. 'targeted_muscles': List all major muscles targeted (e.g. ["Chest", "Shoulders", "Triceps"]). Choose from: Chest, Back, Shoulders, Quads, Hamstrings, Glutes, Calves, Biceps, Triceps, Core, Wrists/Forearms, Hips.
    5. 'muscle_focus': For EACH muscle listed in 'targeted_muscles', determine if the exercise builds "Strength", "Mobility", or both for that muscle. List as a dictionary mapping each muscle to a list. E.g. {{"Shoulders": ["Strength", "Mobility"], "Triceps": ["Strength"]}}.
    6. 'training_types': Identify all applicable training types. Choose from: "Gym", "Calisthenics", "Yoga". (e.g. Dips/Pull-ups are Gym & Calisthenics, Cobra Pose is Yoga).
    7. 'demo_url': Select the best clickable video URL or guide link from the search results above (especially real YouTube video watch URLs like https://www.youtube.com/watch?v=... that match the exercise). If no good video link was found, generate a high-quality YouTube search URL: https://www.youtube.com/results?search_query=EXERCISE+NAME+tutorial+form
    8. 'levels': Identify the experience levels this exercise is suitable for. Choose from: "Beginner", "Intermediate", "Advanced". Multiple values are highly encouraged!
    9. 'next_level_progressions': List any exercise names that represent the next progression/level of difficulty for this exercise (e.g., for "Push-Up", next progression could be "Decline Push-Up" or "Archer Push-Up").
    
    Extract and classify at least 2-5 high-quality, relevant exercises from the search context. Ensure all fields are fully populated and conform strictly to the Pydantic schema.
    """
    
    messages = [HumanMessage(content=prompt)]
    try:
        output = llm_structured.invoke(messages)
        new_exercises = output.exercises
        
        # Save them to the library
        for ex in new_exercises:
            add_or_update_exercise(ex)
            
        return new_exercises
    except Exception as e:
        print(f"Error in LLM browser search flow: {e}")
        # Return empty list on failure
        return []
