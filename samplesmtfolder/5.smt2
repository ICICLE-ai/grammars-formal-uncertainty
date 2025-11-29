(assert 
  (forall ((x Person))
    (= (Succeeds x)
       (or (StudiesMath x)
           (and (StudiesPhysics x) (WorksHard x))))))