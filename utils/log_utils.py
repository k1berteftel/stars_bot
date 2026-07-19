

def write_log(log_text: str):
    with open('payment_log.txt', 'a+', encoding='utf-8') as f:
        f.write(log_text)