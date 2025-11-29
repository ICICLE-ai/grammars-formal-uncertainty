(assert 
  (forall ((x Person))
    (=> (WorksHard x)
        (=> (or (StudiesMath x) (StudiesPhysics x))
            (Succeeds x)))))