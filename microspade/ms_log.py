# microbit-module: ms_log@0.1.0

def log_kb(agent):
    """Log the agent's knowledge base (KB) to the micro:bit flash memory."""
    if agent._log_state is False:
        return

    try:
        import log
    except ImportError:
        # Fallback for desktop/testing environment
        print("[Log Mock] Logging KB:", agent._kb)
        return

    if agent._kb:
        if agent._log_state is None:
            # Set column headers using the dictionary keys
            log.set_labels(*agent._kb.keys())
            agent._log_state = True
        
        try:
            log.add(**agent._kb)
        except OSError as e:
            # Error 28 means disk full (ENOSPC)
            if len(e.args) > 0 and e.args[0] == 28:
                print("[Log] Memory full. Fast-deleting log to continue...")
                log.delete(full=False)
                # After deletion, labels must be re-registered
                log.set_labels(*agent._kb.keys())
                # Retry logging the current row
                try:
                    log.add(**agent._kb)
                except OSError:
                    # If it still fails, deactivate logging to prevent loops
                    agent._log_state = False
                    print("[Log] Critical: Deletion failed or disk still full.")
            else:
                raise e
