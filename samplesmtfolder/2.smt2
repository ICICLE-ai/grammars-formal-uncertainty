(assert 
  (forall ((x Person))
    (=> (and (or (StudiesMath x) (StudiesPhysics x))
             (WorksHard x))
        (Succeeds x))))