(assert 
  (forall ((x Person))
    (=> (or (StudiesMath x) 
            (and (StudiesPhysics x) (WorksHard x)))
        (Succeeds x))))