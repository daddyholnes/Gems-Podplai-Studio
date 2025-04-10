# example_usage.py
from chat_memory_buffer import chat_with_memory
import os


def demonstrate_conversation():
    # First interaction
    print("User: What is the latest news about the US Stock Market?")
    response = chat_with_memory("What is the latest news about the US Stock Market?")
    print(f"Assistant: {response}\n")

    # Follow-up question using memory
    print("User: How does this compare to its performance last week?")
    response = chat_with_memory("How does this compare to its performance last week?")
    print(f"Assistant: {response}\n")

    # Cross-session persistence demo
    print("User: Save this conversation about the US stock market.")
    chat_with_memory("Save this conversation about the US stock market.")
    
    # New session
    print("\n--- New Session ---")
    print("User: What were we discussing earlier?")
    response = chat_with_memory("What were we discussing earlier?")
    print(f"Assistant: {response}")

if __name__ == "__main__":
    demonstrate_conversation()

