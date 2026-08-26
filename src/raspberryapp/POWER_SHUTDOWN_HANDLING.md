# Power Shutdown Handling in Motorised Store

## Overview

The new architecture includes comprehensive power shutdown handling to ensure the store can recover gracefully from unexpected power losses.

## How Power Shutdown is Handled

### **1. State Preservation During Operation**

#### **What IS Preserved:**
- ✅ **Position Data**: Continuously saved to `/tmp/motorised_store_position.txt`
- ✅ **Max Time**: Saved to `/tmp/motorised_store_max_time.txt` for calculations
- ✅ **Recovery Data**: Saved to `/tmp/motorised_store_recovery.json` during movement

#### **What is NOT Preserved:**
- ❌ **Current State** (STOPPED, MOVING_UP, etc.) - Lost on power loss
- ❌ **Target Position** - Lost on power loss  
- ❌ **Button States** - Lost on power loss
- ❌ **Threading State** - Lost on power loss

### **2. Power Shutdown Scenarios**

#### **Scenario A: Store is STOPPED**
```
Before Power Loss: Store at 45% position, state = STOPPED
After Power Loss:  Store at 45% position, state = STOPPED (recovered)
Result: ✅ SAFE - Position preserved, store resumes correctly
```

#### **Scenario B: Store is MOVING (Power Loss During Movement)**
```
Before Power Loss: Store moving UP from 50% to 30%, 2 seconds into movement
After Power Loss:  Store estimated at 46% position (calculated from movement time)
Result: ⚠️  RECOVERY NEEDED - Position estimated, manual verification recommended
```

#### **Scenario C: Store is CALIBRATING**
```
Before Power Loss: Store calibrating, position = 0%
After Power Loss:  Store at estimated position based on calibration time
Result: ⚠️  RECOVERY NEEDED - Calibration may be incomplete
```

### **3. Recovery Data Structure**

The system saves recovery data to `/tmp/motorised_store_recovery.json`:

```json
{
    "movement_in_progress": true,
    "direction": "up",
    "start_time": 1704067200.123,
    "timestamp": 1704067200.123
}
```

### **4. Power Loss Detection and Recovery**

#### **On Startup:**
1. **Load Position**: Read `/tmp/motorised_store_position.txt`
2. **Check Recovery File**: Look for `/tmp/motorised_store_recovery.json`
3. **If Recovery Needed**:
   - Calculate estimated position based on movement time
   - Log warning messages
   - Set recovery flag for user notification

#### **Recovery Calculation:**
```python
# Example: Store was moving UP for 3 seconds before power loss
movement_time = 3.0  # seconds
max_time = 30.0      # seconds (from max_time file)
movement_percentage = (3.0 / 30.0) * 100 = 10%

# If store was at 50% and moving UP for 3 seconds
estimated_position = 50% - 10% = 40%
```

### **5. User Interface for Power Loss Recovery**

#### **CLI Status Command:**
```bash
python3 new_cli_control.py status
```

**Normal Output:**
```
Store Status:
  State: stopped
  Position: 45.0%
  Moving: false
```

**Power Loss Recovery Output:**
```
Store Status:
  State: stopped
  Position: 40.0%
  Moving: false

⚠️  POWER LOSS RECOVERY DETECTED:
  Last direction: up
  Estimated position: 40.0%
  Recommendation: Please verify position manually and recalibrate if needed
  Consider running 'calibrate' to verify position
```

#### **Recovery Actions:**
1. **Verify Position**: Manually check if store is at estimated position
2. **Recalibrate if Needed**: Run `python3 new_cli_control.py calibrate`
3. **Continue Normal Operation**: Once position is verified

### **6. File System Recovery**

#### **Recovery Files:**
- `/tmp/motorised_store_position.txt` - Current position (0-100)
- `/tmp/motorised_store_max_time.txt` - Maximum movement time
- `/tmp/motorised_store_recovery.json` - Power loss recovery data (temporary)

#### **File Persistence:**
- **Position File**: Persists across reboots
- **Max Time File**: Persists across reboots  
- **Recovery File**: Automatically deleted after recovery

### **7. Safety Considerations**

#### **Power Loss During Movement:**
- **Position Estimation**: Based on movement time and direction
- **Safety Margin**: Conservative estimates to prevent over-travel
- **User Verification**: Always recommend manual position verification

#### **Power Loss During Calibration:**
- **Calibration Restart**: May need to restart calibration process
- **Position Reset**: Position may be reset to 0% (top)
- **Manual Verification**: Always verify position after power loss

### **8. Best Practices**

#### **For Users:**
1. **Check Status After Power Loss**: Always run `status` command after power restoration
2. **Verify Position**: Manually verify store position if recovery is detected
3. **Recalibrate if Uncertain**: When in doubt, run calibration
4. **Monitor Logs**: Check logs for power loss warnings

#### **For Developers:**
1. **Test Power Loss Scenarios**: Test with power loss during movement
2. **Verify Recovery Logic**: Ensure position calculations are accurate
3. **Monitor File System**: Ensure recovery files are properly managed
4. **Handle Edge Cases**: Test with corrupted or missing recovery files

### **9. Testing Power Loss Recovery**

#### **Simulate Power Loss:**
```bash
# Start store movement
python3 new_cli_control.py up

# Simulate power loss (kill process)
# Wait a few seconds, then restart

# Check recovery
python3 new_cli_control.py status
```

#### **Test Recovery Scenarios:**
1. **Power loss during UP movement**
2. **Power loss during DOWN movement**
3. **Power loss during calibration**
4. **Power loss when stopped**
5. **Multiple power losses in sequence**

### **10. Troubleshooting**

#### **Common Issues:**

**Issue**: Position shows as "Unknown" after power loss
**Solution**: Run calibration to establish position reference

**Issue**: Estimated position seems incorrect
**Solution**: Manually verify position and recalibrate if needed

**Issue**: Recovery file not found
**Solution**: Normal behavior - no recovery needed

**Issue**: Position file corrupted
**Solution**: Delete position file and run calibration

#### **Recovery Commands:**
```bash
# Check current status
python3 new_cli_control.py status

# Recalibrate if needed
python3 new_cli_control.py calibrate

# Move to known position
python3 new_cli_control.py to 0    # Move to top
python3 new_cli_control.py to 100  # Move to bottom
```

## Conclusion

The new architecture provides robust power shutdown handling with:

- **Automatic Position Estimation** after power loss
- **Clear User Notifications** when recovery is needed
- **Safe Recovery Procedures** with manual verification
- **Comprehensive Logging** for troubleshooting
- **File System Persistence** for critical data

This ensures the store can recover gracefully from unexpected power losses while maintaining safety and accuracy.
