"""Test if direct state mutation works with InjectedState"""
from langchain_core.messages import HumanMessage
from app.agent.graph import agent
import json

config = {"configurable": {"thread_id": "test-mutation"}}

print("Testing direct state mutation...")
print("=" * 60)

result = agent.invoke(
    {"messages": [HumanMessage(content="Create a file called hello.txt with the content 'Hello World'")]},
    config=config
)

print("\nChecking state after invocation...")
state = agent.get_state(config=config)
files = state.values.get("files", {})

print(f"\nFiles in state: {list(files.keys())}")

if "hello.txt" in files:
    print(f"✅ SUCCESS! File created: hello.txt")
    print(f"Content: {files['hello.txt']}")
else:
    print(f"❌ FAILED! File not in state")
    print(f"Files dict: {files}")

