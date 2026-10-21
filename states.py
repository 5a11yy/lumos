from aiogram.fsm.state import State, StatesGroup

class Form(StatesGroup):
    name = State()
    age = State()
    city = State()


class Order(StatesGroup):
    product = State()
    quantity = State()
    color = State()