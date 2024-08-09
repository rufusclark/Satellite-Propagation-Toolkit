def autoport() -> str:
    """returns the str port device of first connected serial device

    Raises:
        Error if no ports are connected

    Returns:
        port e.g. "COM3"
    """
    import serial.tools.list_ports

    try:
        return serial.tools.list_ports.comports()[0].device
    except Exception as e:
        raise Exception("No ports found", e)
