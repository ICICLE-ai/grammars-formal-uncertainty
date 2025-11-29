(assert 
  (or (forall ((x Person))
        (=> (StudiesMath x) (Succeeds x)))
      (forall ((x Person))
        (=> (and (StudiesPhysics x) (WorksHard x))
            (Succeeds x)))))