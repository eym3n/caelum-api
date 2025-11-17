# Deployment Fixer Node

Specialized LLM node for automatically diagnosing and fixing deployment errors.

## Overview

The **Deployment Fixer** is a dedicated agent node that activates when Vercel deployments fail. Unlike the general Coder node, it focuses exclusively on deployment-blocking issues with a specialized prompt and error analysis capabilities.

## Architecture

### Agent Flow

```
Designer → Coder → Deployer
                      ↓
                  [Success?]
                      ↓
            Yes ──────┴────── No
             ↓                 ↓
            END         Deployment Fixer
                              ↓
                     [Makes Fixes via Tools]
                              ↓
                          Deployer (retry)
                              ↓
                         [Loop until success]
```

### State Management

The deployment fixer uses three state flags:

```python
# BuilderState fields
deployment_failed: bool          # True when deployment fails
deployment_error: str            # Full error message from Vercel
deployment_fixer_run: bool       # True when fixer makes changes
```

## How It Works

### 1. Trigger

When the **Deployer** node fails (non-zero exit code, timeout, or exception):
- Sets `deployment_failed = True`
- Captures full error output in `deployment_error`
- Routes to **Deployment Fixer** instead of ending

### 2. Analysis

The Deployment Fixer:
- Receives the full deployment error log
- Gets list of all files in the session
- Uses specialized prompt focused on deployment issues
- Analyzes the error to identify root cause

### 3. Fixes

Common issues it can fix:
- **Build Errors**: TypeScript compilation, import issues
- **Missing Dependencies**: Updates package.json
- **Configuration**: Fixes next.config.js, tsconfig.json
- **Next.js Issues**: Adds 'use client' directives, fixes API routes
- **File Issues**: Resolves path problems, missing files

### 4. Re-deployment

After making fixes:
- Sets `deployment_fixer_run = True`
- Routes back to **Deployer** for retry
- Process repeats until deployment succeeds or gives up

## Specialized Prompt

The Deployment Fixer uses a specialized prompt that:

### Focuses On
- ✅ Deployment-specific errors
- ✅ Build failures
- ✅ Vercel-specific issues
- ✅ Next.js configuration problems
- ✅ Dependency issues

### Avoids
- ❌ General code refactoring
- ❌ Feature improvements
- ❌ Style/formatting changes
- ❌ Non-blocking issues

### Key Sections

1. **Error Context**: Full deployment error displayed prominently
2. **Common Issues**: Checklist of typical deployment problems
3. **Process**: Step-by-step approach to fixing
4. **Tools**: Available file and command tools
5. **Rules**: Strict guidelines to stay focused

## Available Tools

The Deployment Fixer has access to the same tools as the Coder:

### File Operations (Batch)
```python
- batch_read_files    # Read multiple files
- batch_create_files  # Create new files
- batch_update_files  # Update file contents
- batch_delete_files  # Remove files
- batch_update_lines  # Precise line updates
- list_files          # See available files
```

### Validation
```python
- lint_project        # Check for syntax errors
```

## Example Scenarios

### Scenario 1: Missing Dependency

**Error:**
```
Module not found: Can't resolve 'framer-motion'
```

**Fix:**
1. Reads `package.json`
2. Adds `"framer-motion": "^10.0.0"` to dependencies
3. Saves file
4. Runs lint check
5. Deployment retries → Success

### Scenario 2: Missing 'use client'

**Error:**
```
Error: useState can only be used in Client Components
```

**Fix:**
1. Reads the component file
2. Adds `'use client'` directive at the top
3. Saves file
4. Deployment retries → Success

### Scenario 3: Invalid Config

**Error:**
```
Invalid next.config.js: module.exports is not defined
```

**Fix:**
1. Reads `next.config.js`
2. Fixes syntax (adds proper module.exports)
3. Verifies configuration structure
4. Deployment retries → Success

## Configuration

### LLM Settings

```python
model = "gpt-5"
reasoning_effort = "minimal"  # Fast, focused fixes
tool_choice = "any"           # Force tool usage
parallel_tool_calls = True    # Fix multiple issues at once
```

### Retry Logic

The system will continue retrying deployment after fixes until:
- ✅ Deployment succeeds
- ❌ Maximum retries reached (handled by LangGraph)
- ❌ Fixer determines issue is unfixable

## Integration with Landing Pages

The Deployment Fixer integrates with the landing pages system:

```python
# On deployment failure
update_landing_page_status(
    session_id=session_id,
    status=LandingPageStatus.FAILED
)

# After successful retry
update_landing_page_status(
    session_id=session_id,
    status=LandingPageStatus.GENERATED,
    deployment_url=f"https://{session_id}.vercel.app"
)
```

## Monitoring

### Logs

The Deployment Fixer provides detailed logs:

```
[DEPLOYMENT_FIXER] 🔧 Starting deployment error analysis...
[DEPLOYMENT_FIXER] Session: abc123
[DEPLOYMENT_FIXER] Error: Module not found...
[DEPLOYMENT_FIXER] Analyzing deployment error and determining fixes...
[DEPLOYMENT_FIXER] Making 2 fix(es) to resolve deployment error
```

### State Tracking

Monitor deployment fixing progress via state:

```python
state.deployment_failed       # True while failing
state.deployment_error        # Full error message
state.deployment_fixer_run    # True when fixer acts
```

## Best Practices

### For Deployment Errors

1. **Be Specific**: The more detailed the error, the better the fix
2. **Full Context**: Deployment Fixer gets complete error output
3. **Iterative**: System will retry multiple times if needed
4. **Targeted**: Fixes only what's broken, nothing more

### For Error Messages

Ensure deployment script captures:
- ✅ Full build output
- ✅ Stack traces
- ✅ File paths mentioned in errors
- ✅ Line numbers if available

## Comparison: Coder vs Deployment Fixer

| Aspect | Coder | Deployment Fixer |
|--------|-------|------------------|
| **Purpose** | Build features | Fix deployment errors |
| **Trigger** | User requests | Deployment failure |
| **Prompt** | General development | Deployment-specific |
| **Focus** | Feature complete | Deployment success |
| **Scope** | Broad | Narrow (error only) |
| **Tools** | All file + command tools | All file + command tools |
| **Next Step** | Deployer | Deployer (retry) |

## Troubleshooting

### Fixer Not Activating

**Check:**
- Is `deployment_failed` set to `True`?
- Is there content in `deployment_error`?
- Are edges configured correctly in graph?

### Infinite Loop

**Possible Causes:**
- Fixer making changes but error persists
- Error message not clear enough for LLM
- Issue is environmental, not code-related

**Solutions:**
- Add maximum retry limit
- Improve error message capture
- Add manual intervention point

### Not Making Changes

**Possible Causes:**
- LLM not understanding error
- Tool choice not enforced
- Prompt not clear enough

**Solutions:**
- Review `tool_choice="any"` is set
- Enhance error message detail
- Improve prompt specificity

## Future Enhancements

Potential improvements:

- [ ] Track number of retry attempts
- [ ] Add confidence scoring for fixes
- [ ] Learn from successful fixes (RAG)
- [ ] Support for other deployment platforms
- [ ] Parallel fix attempts for multiple errors
- [ ] Integration with deployment logs API
- [ ] Automated testing before redeployment

## Code Reference

- **Node**: `app/agent/nodes/deployment_fixer.py`
- **State**: `app/agent/state.py` (`deployment_fixer_run` field)
- **Graph**: `app/agent/graph.py` (edges and routing)
- **Prompt**: Built into `deployment_fixer.py` (`DEPLOYMENT_FIXER_PROMPT`)

## Summary

The Deployment Fixer provides:
- 🎯 **Focused**: Specialized for deployment errors
- 🔄 **Automatic**: No manual intervention needed
- 🔧 **Precise**: Targeted fixes, minimal changes
- 📊 **Integrated**: Works with landing pages system
- 🚀 **Fast**: Minimal reasoning for quick fixes

This ensures deployments succeed automatically, even when errors occur! 🎉

