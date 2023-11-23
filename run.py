async def create_table(data, is_pending=True):
    table = PrettyTable()
    headers = ["Id", "Time", "Type", "Symbol", "Size", "Entry", "SL", "TP", "Profit"]
    if not is_pending:
        headers.remove("Profit")
    table.field_names = headers

    try:
        # Kiểm tra xem data có phải là chuỗi không
        if isinstance(data, str):
            # Nếu là chuỗi, chuyển đổi thành đối tượng Python
            json_data = json.loads(data)
        elif isinstance(data, dict):
            # Nếu là từ điển, sử dụng trực tiếp
            json_data = data
        else:
            # Nếu không phải là chuỗi hoặc từ điển, xử lý lỗi hoặc trả về
            raise ValueError("Invalid data format")

        for position in json_data.get("positions", []):
            row = [
                position.get("id", ""),
                position.get("time", ""),
                position.get("type", ""),
                position.get("symbol", ""),
                position.get("volume", ""),
                position.get("openPrice", ""),
                position.get("stopLoss", ""),
                position.get("takeProfit", ""),
                position.get("profit", "") if not is_pending else None
            ]
            table.add_row(row)

        return table
    except Exception as e:
        # Xử lý lỗi khi có vấn đề với định dạng dữ liệu
        print(f"Error creating table: {e}")
        return None
