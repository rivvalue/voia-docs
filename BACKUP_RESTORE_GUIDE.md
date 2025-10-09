# VOÏA Database Checkpoint & Rollback Guide

## Overview
This guide provides comprehensive instructions for managing checkpoints and database rollback during Phase 2b UI migration testing. 

**⚠️ CRITICAL: For Phase 2b, use Replit's built-in rollback as the PRIMARY backup mechanism.**

VOÏA provides two backup strategies:
1. **Replit Rollback** (PRIMARY - RECOMMENDED) - Integrated, reliable, restores code + files + database atomically
2. **SQLAlchemy Backup** (SUPPLEMENTARY) - Experimental database-only JSON export with known limitations

## Backup Strategy Comparison

| Feature | Replit Rollback | SQLAlchemy Backup |
|---------|----------------|-------------------|
| **Reliability** | ✅ Production-grade | ⚠️ Experimental |
| **Database Restore** | ✅ Guaranteed | ⚠️ Best-effort |
| **Code Restore** | ✅ Yes | ❌ No |
| **File Restore** | ✅ Yes | ❌ No |
| **FK Handling** | ✅ Automatic | ⚠️ Requires privileges |
| **Sequence Reset** | ✅ Automatic | ⚠️ Manual |
| **Type Safety** | ✅ Native | ⚠️ JSON conversion |
| **Phase 2b Ready** | ✅ Yes | ⚠️ Use with caution |

**RECOMMENDATION:** Always use Replit Rollback for Phase 2b safety. Use SQLAlchemy backup only for:
- Database-only snapshots (when code doesn't need rollback)
- Experimental testing
- Data export/analysis

## Quick Reference

### Create a Checkpoint
```bash
# Phase 2b checkpoint with tags
python backup_utils.py checkpoint "pre_sidebar_migration" "Before sidebar navigation implementation" --tag phase2b

# Daily development checkpoint
python backup_utils.py checkpoint "dev_checkpoint" "End of day checkpoint" --tag daily
```

### List Checkpoints
```bash
# List all checkpoints
python backup_utils.py list

# List Phase 2b checkpoints only
python backup_utils.py list --tag phase2b
```

### Show Checkpoint Details
```bash
python backup_utils.py show "pre_sidebar_migration"
```

### Restore (Rollback)
**Use Replit UI:**
1. Click **Tools > Rollback** in Replit interface
2. Find the checkpoint by timestamp and description
3. Click **Rollback** to restore code, files, and database

---

## Why Replit Rollback?

### Advantages
- ✅ **Integrated**: Restores code, files, AND database atomically
- ✅ **Safe**: Managed by Replit infrastructure, no version conflicts
- ✅ **UI-Based**: Visual checkpoint selection with previews
- ✅ **Automatic**: Checkpoints created during development automatically
- ✅ **Reliable**: Professional-grade backup system

### Checkpoint Metadata
The `backup_utils.py` provides:
- **Tracking**: Named checkpoints with descriptions
- **Organization**: Tag-based filtering (e.g., `phase2b`, `pre-migration`)
- **Documentation**: Rollback instructions for each checkpoint
- **Searchability**: Find checkpoints by name or tag

---

## Checkpoint Strategy for Phase 2b

### Pre-Migration Checkpoint (CRITICAL)
**Before starting any Phase 2b UI changes:**

```bash
python backup_utils.py checkpoint "phase2b_baseline" "Production state before sidebar nav implementation" --tag phase2b --tag baseline
```

Then create Replit checkpoint:
1. Commit all current changes
2. Replit auto-creates checkpoint
3. Note the timestamp for metadata correlation

### Development Checkpoints
Create checkpoints at key milestones:

```bash
# After sidebar layout complete
python backup_utils.py checkpoint "sidebar_structure_complete" "Basic sidebar navigation structure" --tag phase2b --tag sidebar

# After mobile responsive
python backup_utils.py checkpoint "mobile_responsive_done" "Mobile responsive sidebar complete" --tag phase2b --tag mobile

# Before v2 rollout
python backup_utils.py checkpoint "pre_v2_rollout" "Ready for gradual v2 rollout" --tag phase2b --tag rollout
```

### Daily Checkpoints
During active development:

```bash
# End of day
python backup_utils.py checkpoint "daily_$(date +%Y%m%d)" "Daily checkpoint - [describe work done]" --tag daily
```

---

## Rollback Procedures

### Emergency Rollback (Critical Bug Found)

1. **Open Replit Rollback UI:**
   - Click **Tools > Rollback** in Replit interface

2. **Find the checkpoint:**
   ```bash
   # Check checkpoint metadata first
   python backup_utils.py show "phase2b_baseline"
   ```
   Note the timestamp and description

3. **Select checkpoint in Replit UI:**
   - Look for checkpoint near the timestamp
   - Verify description matches
   - Preview changes if available

4. **Rollback:**
   - Click **Rollback** button
   - Confirm restoration
   - Wait for completion (code, files, database restored)

5. **Verify:**
   - Check application restarts correctly
   - Verify data integrity
   - Test key functionality

### Rollback to Specific Milestone

```bash
# 1. List Phase 2b checkpoints
python backup_utils.py list --tag phase2b

# 2. Show specific checkpoint
python backup_utils.py show "sidebar_structure_complete"

# 3. Use Replit UI to rollback to that timestamp
# (Follow UI instructions from checkpoint metadata)
```

---

## Checkpoint Management

### Viewing Checkpoints

```bash
# All checkpoints
python backup_utils.py list

# Phase 2b only
python backup_utils.py list --tag phase2b

# Daily checkpoints
python backup_utils.py list --tag daily

# Pre-migration checkpoints
python backup_utils.py list --tag pre-migration
```

### Checkpoint Details

```bash
# Show full metadata
python backup_utils.py show "pre_sidebar_migration"

# Output includes:
# - Checkpoint name
# - Creation timestamp
# - Description
# - Tags
# - Rollback instructions
```

### Programmatic Usage

```python
from backup_utils import CheckpointManager

# Initialize manager
checkpoint_mgr = CheckpointManager()

# Create checkpoint
metadata = checkpoint_mgr.create_checkpoint(
    checkpoint_name="automated_checkpoint",
    description="Automated pre-deployment checkpoint",
    tags=["automated", "deployment"]
)

# List checkpoints
checkpoints = checkpoint_mgr.list_checkpoints(tag_filter="phase2b")
for checkpoint in checkpoints:
    print(f"{checkpoint['checkpoint_name']}: {checkpoint['description']}")

# Get specific checkpoint
checkpoint = checkpoint_mgr.get_checkpoint("pre_sidebar_migration")
if checkpoint:
    print(checkpoint['replit_rollback_instructions'])
```

---

## Checkpoint File Structure

### Checkpoint Directory
All checkpoint metadata stored in: `checkpoints/`

### Metadata Files
Each checkpoint creates: `<name>_<timestamp>.json`

Example: `pre_sidebar_migration_20251009_143422.json`
```json
{
  "checkpoint_name": "pre_sidebar_migration",
  "timestamp": "20251009_143422",
  "datetime": "2025-10-09T14:34:22.123456",
  "description": "Before sidebar navigation implementation",
  "tags": ["phase2b", "pre-migration"],
  "replit_rollback_instructions": "To restore to this checkpoint:\n1. Open Replit UI\n2. Click Tools > Rollback\n..."
}
```

---

## Phase 2b Specific Workflows

### Workflow 1: Safe UI Migration Testing

```bash
# 1. Create pre-migration checkpoint
python backup_utils.py checkpoint "phase2b_start" "Clean state before any UI changes" --tag phase2b --tag baseline

# 2. Implement sidebar UI changes
# ... development work ...

# 3. Create progress checkpoint
python backup_utils.py checkpoint "sidebar_wip" "Sidebar work in progress" --tag phase2b --tag wip

# 4. If issues found, rollback via Replit UI
#    (Use timestamp from "phase2b_start" checkpoint)

# 5. If successful, create success checkpoint
python backup_utils.py checkpoint "sidebar_success" "Working sidebar implementation" --tag phase2b --tag milestone
```

### Workflow 2: Gradual Rollout with Rollback Plan

```bash
# 1. Before enabling 10% rollout
python backup_utils.py checkpoint "pre_rollout_10pct" "Before 10% user rollout" --tag phase2b --tag rollout

# 2. Set SIDEBAR_ROLLOUT_PERCENTAGE=10 and monitor

# 3. If critical issues detected:
#    - Use Replit UI > Tools > Rollback
#    - Select checkpoint from "pre_rollout_10pct" timestamp
#    - Set SIDEBAR_ROLLOUT_PERCENTAGE=0

# 4. Before increasing to 25%
python backup_utils.py checkpoint "pre_rollout_25pct" "Before 25% user rollout" --tag phase2b --tag rollout
```

### Workflow 3: Feature Development Cycle

```bash
# Start feature
python backup_utils.py checkpoint "feature_start" "Starting feature X" --tag feature-x

# Development iterations
# ... code, test, iterate ...

# Feature complete
python backup_utils.py checkpoint "feature_complete" "Feature X complete and tested" --tag feature-x --tag complete

# If rollback needed, use Replit UI to restore to "feature_start"
```

---

## Best Practices

### 1. Always Checkpoint Before Major Changes
- ✅ Before Phase 2b migration
- ✅ Before database schema changes
- ✅ Before production deployments
- ✅ Before bulk data operations

### 2. Use Descriptive Names and Tags
```bash
# ❌ Bad
python backup_utils.py checkpoint "checkpoint1"

# ✅ Good
python backup_utils.py checkpoint "pre_sidebar_migration" "Production state before Phase 2b" --tag phase2b --tag baseline
```

### 3. Tag Consistently
Common tag patterns:
- `phase2b` - All Phase 2b related checkpoints
- `baseline` - Starting point checkpoints
- `milestone` - Major completion checkpoints
- `wip` - Work in progress checkpoints
- `rollout` - Deployment/rollout checkpoints
- `daily` - Daily development checkpoints

### 4. Document Checkpoint Context
Always include what the checkpoint represents:

```bash
python backup_utils.py checkpoint "critical_fix" "Before applying hotfix for issue #1234" --tag hotfix
```

### 5. Correlate with Replit Checkpoints
When creating checkpoint metadata:
1. Create the metadata first
2. Commit changes (triggers Replit checkpoint)
3. Note both timestamps for correlation

---

## Recovery Scenarios

### Scenario 1: UI Migration Breaks Functionality
**Symptom:** Sidebar navigation causes crashes

**Recovery:**
1. Check checkpoint metadata:
   ```bash
   python backup_utils.py show "phase2b_baseline"
   ```
2. Use Replit UI > Tools > Rollback
3. Select checkpoint matching "phase2b_baseline" timestamp
4. Rollback to restore working state
5. Analyze issue before retry

### Scenario 2: Partial Feature Rollback
**Symptom:** Need to rollback sidebar but keep other changes

**Note:** Replit rollback is atomic (all or nothing)

**Options:**
- Full rollback + cherry-pick needed changes
- Manual code reversion for specific files
- Create branch before Phase 2b for comparison

### Scenario 3: Lost Work Recovery
**Symptom:** Accidentally deleted important code

**Recovery:**
1. List recent checkpoints:
   ```bash
   python backup_utils.py list --tag daily
   ```
2. Find most recent checkpoint before deletion
3. Use Replit rollback to restore
4. Extract needed code from restored state

---

## Integration with Feature Flags

Checkpoints work with feature flags for safe rollout:

```bash
# 1. Baseline checkpoint
python backup_utils.py checkpoint "v1_baseline" "V1 UI baseline" --tag baseline

# 2. Implement v2 UI (feature flag controlled)
# ... development ...

# 3. Enable for testing (FEATURE_UI_TOGGLE=true)
python backup_utils.py checkpoint "v2_testing" "V2 UI ready for testing" --tag v2 --tag testing

# 4. Start rollout (SIDEBAR_ROLLOUT_PERCENTAGE=10)
python backup_utils.py checkpoint "v2_rollout_10" "V2 UI 10% rollout" --tag v2 --tag rollout

# 5. If issues, rollback via Replit UI to "v1_baseline"
#    Set SIDEBAR_ROLLOUT_PERCENTAGE=0
```

---

## Monitoring and Alerts

### Checkpoint Health Checks
Periodically verify checkpoint system:

```bash
# Check checkpoint metadata exists
python backup_utils.py list | head -10

# Verify recent checkpoints
python backup_utils.py list --tag phase2b
```

### Rollback Readiness
Before major changes, verify rollback capability:

1. Create test checkpoint
2. Note timestamp
3. Verify visible in Replit UI > Tools > Rollback
4. Confirm description matches

---

## Troubleshooting

### Issue: "Checkpoint metadata not found"
**Solution:**
```bash
# List all checkpoints
python backup_utils.py list

# Check checkpoint directory
ls -la checkpoints/

# Recreate checkpoint if needed
python backup_utils.py checkpoint "recovery_checkpoint" "Recovery checkpoint" --tag recovery
```

### Issue: "Cannot find checkpoint in Replit UI"
**Cause:** Replit checkpoints are created on commits/significant changes

**Solution:**
1. Checkpoint metadata is for tracking only
2. Replit creates actual rollback points automatically
3. Use timestamp and description to correlate
4. If no Replit checkpoint near timestamp, create one by committing changes

### Issue: "Rollback restored wrong version"
**Cause:** Selected wrong checkpoint in Replit UI

**Solution:**
1. Check checkpoint metadata for exact timestamp
2. Re-rollback to correct checkpoint
3. Verify description matches before confirming

---

## Automation Examples

### Pre-Deployment Script
```bash
#!/bin/bash
# pre-deploy.sh

echo "Creating pre-deployment checkpoint..."
python backup_utils.py checkpoint "pre_deploy_$(date +%Y%m%d_%H%M%S)" "Automated pre-deployment checkpoint" --tag deployment

if [ $? -eq 0 ]; then
    echo "✅ Checkpoint created, proceeding with deployment"
    # Trigger Replit checkpoint via commit
    git add . && git commit -m "Pre-deployment checkpoint"
    exit 0
else
    echo "❌ Checkpoint creation failed, aborting deployment"
    exit 1
fi
```

### Daily Checkpoint Automation
```bash
#!/bin/bash
# daily-checkpoint.sh

# Create daily checkpoint
python backup_utils.py checkpoint "daily_$(date +%Y%m%d)" "Daily development checkpoint - $(git log -1 --pretty=%B)" --tag daily

# Clean up old daily checkpoints (keep last 7 days)
find checkpoints/ -name "daily_*.json" -mtime +7 -delete
```

---

## Comparison: Replit Rollback vs Manual Backup

| Feature | Replit Rollback | Manual pg_dump |
|---------|----------------|----------------|
| **Code Restore** | ✅ Yes | ❌ No |
| **File Restore** | ✅ Yes | ❌ No |
| **Database Restore** | ✅ Yes | ✅ Yes |
| **Atomic Operation** | ✅ Yes | ❌ No |
| **UI-Based** | ✅ Yes | ❌ CLI only |
| **Version Compatibility** | ✅ Guaranteed | ⚠️ Version issues |
| **Infrastructure** | ✅ Managed | ⚠️ DIY |
| **Checkpoint Tracking** | ⚠️ Timestamp only | ✅ With metadata |

**Recommendation:** Use Replit Rollback + checkpoint metadata for best of both worlds.

---

## Support and Resources

### Replit Rollback Documentation
- Access: Replit UI > Help > Rollback
- Features: Code, files, database restoration
- Limits: Based on Replit plan

### VOÏA Checkpoint Metadata
- Location: `checkpoints/` directory
- Usage: Tracking and documentation
- CLI: `python backup_utils.py --help`

### Critical Issues
1. Check checkpoint metadata: `python backup_utils.py show <name>`
2. Use Replit UI for actual rollback
3. Consult team lead if issues persist
4. Escalate to Replit support for infrastructure issues

---

## Appendix: Replit Rollback Guide

### Accessing Rollback UI
1. Open Replit workspace
2. Click **Tools** in top menu
3. Select **Rollback**
4. Browse checkpoint history

### Selecting Checkpoint
1. Checkpoints listed by timestamp
2. Hover for preview (if available)
3. Check description matches checkpoint metadata
4. Select desired checkpoint

### Performing Rollback
1. Click **Rollback** button
2. Confirm restoration (warning displayed)
3. Wait for completion (progress indicator)
4. Workspace reloads with restored state

### Post-Rollback
1. Verify code changes
2. Check file system
3. Test database queries
4. Restart application workflows
5. Validate functionality

---

**Last Updated:** October 9, 2025 (Phase 2b Pre-Implementation)  
**Version:** 2.0 (Replit Rollback Integration)  
**Maintainer:** VOÏA Development Team
