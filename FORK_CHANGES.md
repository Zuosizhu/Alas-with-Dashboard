# Alas-with-Dashboard Fork Changes

This document tracks Dashboard-specific modifications that differ from the upstream [LmeSzinc/AzurLaneAutoScript](https://github.com/LmeSzinc/AzurLaneAutoScript) repository. This helps with future upstream syncs and merge conflict resolution.

## Overview

**Fork**: Zuosizhu/Alas-with-Dashboard
**Upstream**: LmeSzinc/AzurLaneAutoScript
**Last Sync**: 2026-01-25 (upstream commit: 252e086db)

## Major Dashboard-Specific Features

### 1. Resource Logging System (LogRes)

**Location**: `module/log_res/`

**Purpose**: Tracks game resources (coins, oil, PT, etc.) with timestamps for Dashboard UI display.

**Files Added**:
- `module/log_res/log_res.py` - Core logging implementation
- Related config in Dashboard settings

**Integration Points** (9 files):
- `module/coalition/coalition.py` - PT logging
- `module/campaign/campaign_status.py` - Campaign resource tracking
- `module/gacha/gacha_reward.py` - Gacha rewards
- `module/os_handler/action_point.py` - Operation Siren AP
- `module/os_handler/os_status.py` - OS status tracking
- `module/raid/raid.py` - Raid resources
- `module/shop/shop_status.py` - Shop inventory
- `module/webui/app.py` - Dashboard UI backend

**Merge Considerations**:
- When upstream changes resource detection code, ensure LogRes calls are preserved
- LogRes typically appears as: `LogRes(self.config).<ResourceName> = value`
- Always followed by `self.config.update()` to persist changes

### 2. Dashboard Web UI

**Location**: `module/webui/` (enhanced from upstream)

**Changes**:
- Additional endpoints for resource history
- LogRes integration for real-time tracking
- Enhanced status displays

**Merge Considerations**:
- Upstream may modify `module/webui/app.py` - ensure Dashboard-specific routes preserved
- Check `module/webui/patch.py` for Dashboard customizations

## Known Merge Conflict Patterns

### Pattern 1: Coalition PT Reading

**Typical Conflict**: `module/coalition/coalition.py` in `get_event_pt()`

**Dashboard Version**:
```python
pt = ocr.ocr(self.device.image)
LogRes(self.config).Pt = pt
self.config.update()
return pt
```

**Resolution Strategy**:
- Preserve LogRes functionality within upstream's improved logic
- Example (2026-01-25 merge):
  ```python
  for _ in self.loop(timeout=1.5):
      pt = ocr.ocr(self.device.image)
      if pt not in [999999]:
          LogRes(self.config).Pt = pt  # Dashboard addition
          self.config.update()          # Dashboard addition
          break
  ```

### Pattern 2: Import Statements

**Typical Conflict**: `from module.log_res.log_res import LogRes`

**Resolution Strategy**:
- Dashboard needs: `from module.log_res.log_res import LogRes`
- Upstream may add: other imports
- Keep both, clean up formatting (remove double spaces)

### Pattern 3: Config Updates

**Typical Conflict**: Additional `self.config.update()` calls

**Resolution Strategy**:
- Dashboard calls `config.update()` after LogRes to persist
- Upstream may batch updates differently
- Preserve Dashboard's update pattern for LogRes-modified values

## Dashboard-Specific Branches

- `master_Dashboard` - Main Dashboard development branch
- `master_lme` - Tracking branch for upstream changes
- `master` - Integration branch (merges from both)

## Upstream Sync Process

1. **Fetch upstream**: `git fetch upstream`
2. **Check commits**: `git log master..upstream/master`
3. **Create sync branch**: `git checkout -b sync-upstream-YYYY-MM`
4. **Merge**: `git merge upstream/master`
5. **Resolve conflicts**: Focus on LogRes preservation
6. **Test**: Run Dashboard with new changes
7. **Create PR**: To Zuosizhu/Alas-with-Dashboard

## Testing Checklist for Upstream Syncs

### LogRes Integration
- [ ] Coalition PT tracking works
- [ ] Campaign resource logging works
- [ ] OS AP tracking works
- [ ] Raid PT tracking works
- [ ] Dashboard UI displays resource history

### Functional Areas
- [ ] Coalition events (test current event)
- [ ] Campaign runs
- [ ] Operation Siren
- [ ] Raid
- [ ] Shop purchases
- [ ] Gacha pulls

### Dashboard UI
- [ ] Web interface loads
- [ ] Resource graphs display
- [ ] Real-time updates work
- [ ] Historical data preserved

## Common Pitfalls

1. **Don't remove LogRes imports**: Even if they look "unused" to IDE
2. **Don't remove config.update() calls**: Dashboard needs immediate persistence
3. **Check double spaces**: Dashboard originally had `from  module.log_res` (two spaces)
4. **Verify Dashboard config files**: Upstream doesn't have Dashboard-specific config sections

## File Change Summary

### Files Only in Dashboard Fork
- `module/log_res/` (entire directory)
- Dashboard-specific config sections
- Additional web UI templates/routes

### Files Modified from Upstream
- `module/coalition/coalition.py` (+LogRes)
- `module/campaign/campaign_status.py` (+LogRes)
- `module/gacha/gacha_reward.py` (+LogRes)
- `module/os_handler/action_point.py` (+LogRes)
- `module/os_handler/os_status.py` (+LogRes)
- `module/raid/raid.py` (+LogRes)
- `module/shop/shop_status.py` (+LogRes)
- `module/webui/app.py` (+LogRes integration)

### Files Identical to Upstream
- Most other files follow upstream exactly

## Future Considerations

### Upstreaming Dashboard Features
If LogRes proves valuable, consider proposing it to upstream:
- Generic resource tracking framework
- Plugin architecture for optional logging
- Dashboard as optional component

### Reducing Merge Conflicts
- Keep Dashboard changes minimal and focused
- Use inheritance/composition over modification where possible
- Document all deviations from upstream

## References

- **Upstream Repository**: https://github.com/LmeSzinc/AzurLaneAutoScript
- **Fork Repository**: https://github.com/Zuosizhu/Alas-with-Dashboard
- **Latest Sync PR**: https://github.com/Zuosizhu/Alas-with-Dashboard/pull/22

## Changelog

### 2026-01-25: Sync with upstream (19 commits)
- Merged upstream commits up to 252e086db
- Added Fashion event (coalition_20260122) and DAL event (coalition_20251120)
- Integrated LogRes with upstream's improved PT reading timeout loop
- Resolved conflict in `module/coalition/coalition.py`
- Operation Siren refactored into 12 task modules
- QUIT_RECONFIRM assets reorganized

---

*Last Updated*: 2026-01-25
*Maintainer*: Zuosizhu
*Sync Status*: 19 commits behind upstream as of 2026-01-25
