
import traceback


def f(x):
    # print(traceback.extract_stack())  # Полная информация о стеке вызовов
    print(traceback.extract_stack()[-2].lineno)  # Только номер строки, откуда была вызвана функция


f(1)
f(2)
f(3)
print(traceback.extract_stack()[-1].lineno)