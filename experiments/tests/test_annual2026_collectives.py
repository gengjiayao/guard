import unittest
import tempfile
from pathlib import Path
from experiments.annual2026_collectives import generate

class WorkloadDependencyTest(unittest.TestCase):
    def test_ring_has_two_dependency_driven_phases_and_iteration_barrier(self):
        with tempfile.TemporaryDirectory() as directory:
            data=generate('ring1m',1101,Path(directory))
        self.assertEqual(data['flow_count'],16*2*15*2)
        self.assertEqual(len(data['operations']),2)
        self.assertEqual(data['total_bytes'],2*2*15*1024**2)
        first,second=data['operations']
        for root in first['roots']:self.assertEqual(data['dependencies'][root],[])
        for root in second['roots']:self.assertEqual(set(data['dependencies'][root]),set(first['terminals']))
        for op in data['operations']:
            for i in set(op['flows'])-set(op['roots']):
                self.assertEqual(len(data['dependencies'][i]),2)
                predecessors=[data['flows'][p] for p in data['dependencies'][i]]
                self.assertTrue(any(p[1]==data['flows'][i][0] for p in predecessors))

    def test_exchange_preserves_per_rank_volume_and_all_pairs(self):
        with tempfile.TemporaryDirectory() as directory:
            for case in ['alltoall256k','alltoallv']:
                data=generate(case,1101,Path(directory))
                self.assertEqual(data['flow_count'],16*15*2)
                for op in data['operations']:
                    for src in range(16):
                        flows=[data['flows'][i] for i in op['flows'] if data['flows'][i][0]==src]
                        self.assertEqual({f[1] for f in flows},set(range(16))-{src})
                        self.assertEqual(sum(f[3] for f in flows),15*256*1024)

    def test_graphs_are_acyclic_and_reproducible(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for case in ['alltoall256k','alltoallv','ring1m','concurrent']:
                a=generate(case,1101,root/'a');b=generate(case,1101,root/'b')
                self.assertEqual(a['flow_sha256'],b['flow_sha256'])
                self.assertEqual(a['dependency_sha256'],b['dependency_sha256'])
                children=[[] for _ in a['flows']];counts=list(map(len,a['dependencies']))
                for i,parents in enumerate(a['dependencies']):
                    for p in parents:children[p].append(i)
                ready=[i for i,n in enumerate(counts) if not n]
                for i in ready:
                    for child in children[i]:
                        counts[child]-=1
                        if counts[child]==0:ready.append(child)
                self.assertEqual(len(ready),len(a['flows']))

if __name__=='__main__':unittest.main()
