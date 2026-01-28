#!/usr/bin/env python3
"""
Feature Platform CLI with LLM Copilot

Interactive command-line interface for:
1. Chatting with SDK Copilot
2. Generating features from descriptions
3. Getting feature recommendations

Usage:
    python cli.py chat           # Start interactive copilot session
    python cli.py generate       # Generate features from description
    python cli.py recommend      # Get feature recommendations
"""
import argparse
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def chat_mode(api_key: str):
    """Interactive chat with SDK Copilot."""
    from sdk.llm_integration import LLMClient, LLMConfig, SDKCopilot
    
    print("=" * 60)
    print("🤖 Feature Platform SDK Copilot")
    print("=" * 60)
    print("Ask me anything about feature engineering!")
    print("Commands: /clear (reset context), /quit (exit)")
    print("-" * 60)
    
    config = LLMConfig(api_key=api_key)
    client = LLMClient(config)
    copilot = SDKCopilot(client)
    
    while True:
        try:
            user_input = input("\n🧑 You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == "/quit":
                print("Goodbye! 👋")
                break
            
            if user_input.lower() == "/clear":
                copilot.reset()
                print("✅ Context cleared")
                continue
            
            print("\n🤖 Copilot: ", end="", flush=True)
            response = copilot.chat(user_input)
            print(response)
            
        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


def generate_mode(api_key: str):
    """Generate features from natural language."""
    from sdk.llm_integration import LLMClient, LLMConfig, FeatureGenerator
    
    print("=" * 60)
    print("🔧 Feature Generator")
    print("=" * 60)
    print("Describe the features you want to create.")
    print("-" * 60)
    
    description = input("\n📝 Describe your features:\n> ").strip()
    
    if not description:
        print("No description provided.")
        return
    
    print("\n⏳ Generating feature code...\n")
    
    config = LLMConfig(api_key=api_key)
    client = LLMClient(config)
    generator = FeatureGenerator(client)
    
    try:
        code = generator.generate(description)
        print("=" * 60)
        print("📦 Generated Code:")
        print("=" * 60)
        print(code)
        print("=" * 60)
        
        # Offer to save
        save = input("\n💾 Save to sdk/feature_definition.py? (y/n): ").strip().lower()
        if save == 'y':
            feature_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "sdk", "feature_definition.py"
            )
            with open(feature_file, 'a') as f:
                f.write(f"\n\n# Auto-generated feature\n{code}\n")
            print(f"✅ Appended to {feature_file}")
    except Exception as e:
        print(f"❌ Error: {e}")


def recommend_mode(api_key: str):
    """Get feature recommendations."""
    from sdk.llm_integration import LLMClient, LLMConfig, FeatureAdvisor
    
    print("=" * 60)
    print("💡 Feature Advisor")
    print("=" * 60)
    print("Describe your ML use case for personalized recommendations.")
    print("-" * 60)
    
    use_case = input("\n🎯 Use Case (e.g., 'CTR prediction for e-commerce'):\n> ").strip()
    
    if not use_case:
        print("No use case provided.")
        return
    
    # Default schema from our platform
    default_schema = {
        "user_id": "STRING",
        "item_id": "STRING",
        "action_type": "STRING",
        "timestamp": "BIGINT",
        "context": "STRING"
    }
    
    print(f"\n📊 Using default schema: {default_schema}")
    
    print("\n⏳ Getting recommendations...\n")
    
    config = LLMConfig(api_key=api_key)
    client = LLMClient(config)
    advisor = FeatureAdvisor(client)
    
    try:
        recommendations = advisor.recommend(use_case, default_schema)
        print("=" * 60)
        print("💡 Feature Recommendations:")
        print("=" * 60)
        print(recommendations)
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Feature Platform CLI with LLM Copilot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py chat         # Interactive copilot session
  python cli.py generate     # Generate features from description  
  python cli.py recommend    # Get feature recommendations

Environment Variables:
  OPENAI_API_KEY       OpenAI API key
  ANTHROPIC_API_KEY    Anthropic API key (alternative)
        """
    )
    parser.add_argument(
        "command",
        choices=["chat", "generate", "recommend"],
        help="Command to run"
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="API key (or set OPENAI_API_KEY env var)"
    )
    
    args = parser.parse_args()
    
    # Get API key
    api_key = args.api_key or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    
    if not api_key:
        print("❌ Error: No API key found.")
        print("Set OPENAI_API_KEY environment variable or use --api-key flag")
        sys.exit(1)
    
    # Run command
    if args.command == "chat":
        chat_mode(api_key)
    elif args.command == "generate":
        generate_mode(api_key)
    elif args.command == "recommend":
        recommend_mode(api_key)


if __name__ == "__main__":
    main()
