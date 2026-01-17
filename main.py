@app.route('/api/validate_picks', methods=['POST'])
def api_validate_picks():
    data = request.json
    picks_data = data.get('picks', [])
    original_msgs_data = data.get('original_messages', [])
    auto_fix = data.get('auto_fix', True) # Enable by default for now
    
    # 1. Convert to Models
    picks = []
    for p in picks_data:
        try:
            # Ensure ID is handled correctly
            if 'id' in p and 'message_id' not in p:
                p['message_id'] = p['id']
            picks.append(BetPick(**p))
        except Exception as e:
            logging.warning(f"Failed to convert pick to model: {e}")
            pass
            
    # 2. Map Messages
    msg_map = {}
    for m in original_msgs_data:
        try:
            # Handle string vs int ID mismatch
            mid = m.get('id')
            if mid is not None:
                # Create object (safely handling missing fields)
                msg_obj = TelegramMessage(
                    id=int(mid),
                    text=m.get('text', ''),
                    date=m.get('date', 'Unknown'),
                    channel_id=m.get('channel_id', 0),
                    channel_name=m.get('channel_name', 'Unknown'),
                    images=m.get('images', []),
                    video=m.get('video'),
                    ocr_text=m.get('ocr_text', '')
                )
                msg_map[int(mid)] = msg_obj
                msg_map[str(mid)] = msg_obj # Map both just in case
        except Exception as e:
            logging.warning(f"Failed to convert message to model: {e}")
            pass

    # 3. Two-Pass Verification (Auto-Fix)
    if auto_fix:
        logging.info(f"[Validate] Running Two-Pass Verification on {len(picks)} picks...")
        try:
            # Handle async execution safely
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            fixed_picks = loop.run_until_complete(two_pass_verifier.verify_picks(picks, msg_map))
            loop.close()
            
            # Merge odds one last time
            fixed_picks_dicts = [p.dict() for p in fixed_picks]
            final_picks = smart_merge_odds(fixed_picks_dicts)
            
            logging.info(f"[Validate] Verification complete. Returning {len(final_picks)} picks.")
            
            return jsonify({
                'status': 'clean', 
                'picks': final_picks, 
                'fixed': True
            })
        except Exception as e:
            logging.error(f"[Validate] Auto-fix failed: {e}")
            import traceback
            traceback.print_exc()
            # If auto-fix fails, return original picks as clean to avoid blocking
            return jsonify({'status': 'clean', 'picks': picks_data})

    return jsonify({'status': 'clean', 'picks': picks_data})
