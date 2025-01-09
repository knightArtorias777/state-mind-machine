import time


def Countdown(minutes: int):
    seconds = minutes * 60
    while seconds:
        mins, secs = divmod(seconds, 60)
        timer = '{:02d}:{:02d}'.format(mins, secs)
        print(timer, end='\r')
        time.sleep(1)
        seconds -= 1
    print('Time is up!')


if __name__ == "__main__":
    wait_time = 10
    result = input("环境配置开始倒计时吗? : Y/n")
    if result == "Y" or result == "y":
        Countdown(wait_time)
    else:
        print("程序结束")
