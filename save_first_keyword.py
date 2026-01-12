#!/usr/bin/env python3
"""
첫 번째 키워드 데이터 저장
"""
import sys
import json
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from worker.pipeline.db import create_pipeline_run
from worker.pipeline.process_apify_results import process_apify_results
from worker.pipeline.logging import setup_logger

logger = setup_logger("save_first_keyword")

# 첫 번째 키워드의 데이터 (이미 가져온 데이터)
items = [
    {"id":"t3_1q67vnc","parsedId":"1q67vnc","title":"Help! Need special dinner restaurant ideas, close to CBD","body":"Have a big wedding anniversary next Tuesday and just realised we haven't booked anywhere for dinner. We have no idea where to go as we don't get out very often anymore.\n\n  \nPlease help! Looking for somewhere in the City, or close by, that has great quality food, good service and a nice setting. Happy for a set menu / or à la carte. Happy to spend $$$ for a great experience.   \n  \nHave been to Hubert, Aria, Felix, Mr Wongs, Restaurant Leo, Matteo Downtown, Margaret, Customs House, Bistro Pappillion, Pellegrino 2000, Nomad etc in the past.\n\nAt the moment, we have Rockpool, The Bentley, The Malaya, The Charles, Brasserie 1930 and Ragazzi on the list.","contentUrl":"https://www.reddit.com/r/foodies_sydney/comments/1q67vnc/help_need_special_dinner_restaurant_ideas_close/","authorId":"t2_laq41cpbe","parsedAuthorId":"laq41cpbe","authorName":"MonarchMay","parsedCommunityName":"foodies_sydney","communityName":"r/foodies_sydney","communityId":"t5_5bfqr1","parsedCommunityId":"5bfqr1","flair":"Discussion","postType":"text","upVotes":2,"commentsCount":28,"dataType":"post","postUrl":"https://www.reddit.com/r/foodies_sydney/comments/1q67vnc/help_need_special_dinner_restaurant_ideas_close/","createdAt":"2026-01-07T06:20:28.000Z","bodyHtml":"<!-- SC_OFF --><div class=\"md\"><p>Have a big wedding anniversary next Tuesday and just realised we haven&#39;t booked anywhere for dinner. We have no idea where to go as we don&#39;t get out very often anymore.</p>\n\n<p>Please help! Looking for somewhere in the City, or close by, that has great quality food, good service and a nice setting. Happy for a set menu / or à la carte. Happy to spend $$$ for a great experience.   </p>\n\n<p>Have been to Hubert, Aria, Felix, Mr Wongs, Restaurant Leo, Matteo Downtown, Margaret, Customs House, Bistro Pappillion, Pellegrino 2000, Nomad etc in the past.</p>\n\n<p>At the moment, we have Rockpool, The Bentley, The Malaya, The Charles, Brasserie 1930 and Ragazzi on the list.</p>\n</div><!-- SC_ON -->","crawledAt":"2026-01-08T13:07:39.956Z"}
]

run_id = create_pipeline_run("collect", "running")
keyword = "spring dinner ideas"

# 전체 데이터셋에서 가져오기 (MCP를 통해)
# 여기서는 샘플만 저장하고, 실제로는 get-actor-output으로 전체 데이터를 가져와야 함
logger.info(f"Processing keyword: {keyword}, run_id: {run_id}")
logger.info("Note: Full dataset should be fetched using mcp_apify_get-actor-output with datasetId='Yu6o5q1FKWhb4jdcH'")
