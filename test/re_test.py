import re
llm_output = """
Thought: 我需要查天气
Action: search_weather("北京")
Observation: 北京晴天
Thought: 下一步...
"""
match = re.search(r'(Thought:.*?Action:.*?)(?=\n\s*(?:Thought:|Action:|Observation:)|\Z)', llm_output, re.DOTALL)
print(match.group(0))
print("----")
print(match.group(1))
