import pickle
import os
from state import GameState

def get_slot_filename(slot_id: int) -> str:
    """Generate filename for a specific slot. 0 is autosave/quicksave."""
    if slot_id == 0:
        return "quicksave.pkl"
    return f"save_slot_{slot_id}.pkl"

def get_save_metadata(slot_id: int) -> dict:
    """Return dict with save info or None if empty."""
    filename = get_slot_filename(slot_id)
    if not os.path.exists(filename):
        return None
    
    try:
        timestamp = os.path.getmtime(filename)
        from datetime import datetime
        date_str = datetime.fromtimestamp(timestamp).strftime('%Y/%m/%d %H:%M')
        
        # We could load the whole state to get day/gold etc, but that's slow.
        # For now just return file exists info, or maybe peek?
        # Let's peek safely.
        with open(filename, "rb") as f:
            # Just read the object. If it's huge, this might be slow, but for now it's fine.
            # Optimization: We could store a separate .meta file.
            # But let's stick to simple pickle load for now.
            try:
                state = pickle.load(f)
                info = {
                    "exists": True,
                    "date": date_str,
                    "day": getattr(state, "day", "?"),
                    "gold": getattr(state, "gold", "?"),
                    "faction": getattr(state, "player_faction_id", 0)
                }
                return info
            except:
                return {"exists": True, "date": date_str, "error": "Corrupt"}
    except Exception:
        return None

def save_game(state: GameState, slot_id: int = 0) -> bool:
    """
    Save the current game state to a file using pickle.
    slot_id: 0 for quicksave, 1-3 for manual slots.
    Returns True if successful, False otherwise.
    """
    filename = get_slot_filename(slot_id)
    try:
        # pickle.dump will call state.__getstate__() automatically
        with open(filename, "wb") as f:
            pickle.dump(state, f)
        print(f"Game saved successfully to {filename}")
        return True
    except Exception as e:
        print(f"Failed to save game: {e}")
        return False

def load_game(slot_id: int = 0) -> GameState:
    """
    Load game state from a file.
    Returns the loaded GameState object, or None if failed.
    """
    filename = get_slot_filename(slot_id)
    if not os.path.exists(filename):
        print(f"Save file {filename} does not exist.")
        return None
        
    try:
        with open(filename, "rb") as f:
            state = pickle.load(f)
        
        # Post-load validation (optional but good for safety)
        if not isinstance(state, GameState):
            print("Loaded file is not a valid GameState object")
            return None
            
        print(f"Game loaded successfully from {filename}")
        return state
    except Exception as e:
        print(f"Failed to load game: {e}")
        return None
