#!/usr/bin/env python3
"""
Competition Application Automation - Main Entry Point

Execute complete workflow: scraping → parsing → application generation
"""
import sys
from pathlib import Path
from workflow.workflow_execution import WorkflowExecutor



def main():
    """Main entry point for the competition application automation workflow."""
    
    print(" Competition Application Automation System")
    print("=" * 50)
    
    try:
        # Initialize and run workflow
        executor = WorkflowExecutor()
        success = executor.execute_complete_workflow()
        
        if success:
            print("\n Workflow completed successfully!")
            return 0
        else:
            print("\n Workflow failed. Check logs for details.")
            return 1
            
    except KeyboardInterrupt:
        print("\n  Workflow interrupted by user.")
        return 130
    except Exception as e:
        print(f"\n Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())