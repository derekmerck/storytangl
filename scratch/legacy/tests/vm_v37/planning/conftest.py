from tangl.vm import Frame, BuildReceipt, ResolutionPhase as P

def _collect_build_receipts(frame: Frame) -> list[BuildReceipt]:
    receipts: list[BuildReceipt] = []
    for call in frame.phase_receipts.get(P.UPDATE, []):
        result = call.result
        if isinstance(result, list):
            receipts.extend(br for br in result if isinstance(br, BuildReceipt))
    return receipts



