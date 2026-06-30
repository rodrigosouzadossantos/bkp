import petrobras

def test_callable_package():
  obj = petrobras()
  assert obj.name == 'Petrobras'
