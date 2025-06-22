import random
import math

from netqasm.sdk import Qubit
from netqasm.sdk.classical_communication.message import StructuredMessage

from squidasm.sim.stack.program import Program, ProgramContext, ProgramMeta
from squidasm.util.routines import (
    distributed_CNOT_control,
    distributed_CNOT_target, teleport_send, teleport_recv,
)

class SenderProgram(Program):
    PEER_NAME1 = "Node1"
    PEER_NAME2 = "Node2"

    def __init__(self, m):
        self.m = m

    def prepare_state(self, q0: Qubit, q1: Qubit, q2: Qubit, q3: Qubit):
        q0.H()
        q1.H()
        q2.H()

        q0.rot_Z(angle=-0.73304)
        q2.rot_Z(angle=2.67908)

        q2.cnot(q0)

        q2.H()
        q0.rot_Y(angle=-2.67908)

        q1.cnot(q0)
        q2.cnot(q3)

        q2.rot_Z(angle=1.5708)

        q1.cnot(q3)
        q0.cnot(q2)


    @property
    def meta(self) -> ProgramMeta:
        return ProgramMeta(
            name="sender_program",
            csockets=[self.PEER_NAME1,self.PEER_NAME2],
            epr_sockets=[self.PEER_NAME1,self.PEER_NAME2],
            max_qubits=4,
        )

    def run(self, context: ProgramContext):

        csocket1 = context.csockets[self.PEER_NAME1]
        csocket2 = context.csockets[self.PEER_NAME2]
        connection = context.connection

        #Choose random bit of information
        xs = random.choice([0, 1])
        checkset = set()

        #Send bit of information
        csocket1.send(xs)
        csocket2.send(xs)

        for idx in range(self.m):
            #Implement the circuit
            q0 = Qubit(connection)
            q1 = Qubit(connection)
            q2 = Qubit(connection)
            q3 = Qubit(connection)

            self.prepare_state(q0,q1,q2,q3)

            #Measure Qubits
            r0 = q0.measure()
            r1 = q1.measure()

            #Distribute the qubits, q2 and q3 are inactive now
            yield from teleport_send(q=q2,context=context, peer_name=self.PEER_NAME1)
            yield from teleport_send(q=q3, context=context, peer_name=self.PEER_NAME2)
            yield from connection.flush()



            if r0==xs and r1==xs:
                checkset.add(idx)


        #Send checkset
        csocket1.send(checkset)
        csocket2.send(checkset)
        yield from connection.flush()

        ys = xs
        print(f"Sender result {ys}")
        return {"xs": xs}


class Node1Program(Program):
    SENDER = "Sender"
    PEER_NAME = "Node2"

    def __init__(self, m: int, mu: float, lam: float):
        self.m = m
        self.mu = mu
        self.lam = lam

    @property
    def meta(self) -> ProgramMeta:
        return ProgramMeta(
            name="node1_program",
            csockets=[self.PEER_NAME,self.SENDER],
            epr_sockets=[self.SENDER],
            max_qubits=2,
        )

    def run(self, context: ProgramContext):

        csocket_s = context.csockets[self.SENDER]
        csocket_n = context.csockets[self.PEER_NAME]
        connection = context.connection

        #INVOCATION PHASE
        #Receive bit of information
        xj = yield from csocket_s.recv()

        measurements = []
        for idx in range(self.m):
            #Receive qubit
            q2 = yield from teleport_recv(context=context, peer_name=self.SENDER)

            r2 = q2.measure()
            yield from connection.flush()
            measurements.append(int(r2))

        checkset = yield from csocket_s.recv()

        #CHECK PHASE
        T = math.ceil(self.mu * self.m)
        if len(checkset) >= T and all(measurements[i] != xj for i in checkset):
            y0 = xj
        else:
            y0 = None

        #CROSS-CALLING PHASE
        csocket_n.send(y0)
        csocket_n.send(checkset)
        connection.flush()

        print(f"Node 1 result: {y0}")

        return {"y0": y0}

class Node2Program(Program):
    SENDER = "Sender"
    PEER_NAME = "Node1"

    def __init__(self, m: int, mu: float, lam: float):
        self.m = m
        self.mu = mu
        self.lam = lam

    @property
    def meta(self) -> ProgramMeta:
        return ProgramMeta(
            name="node2_program",
            csockets=[self.PEER_NAME, self.SENDER],
            epr_sockets=[self.SENDER],
            max_qubits=2,
        )

    def run(self, context: ProgramContext):

        csocket_s = context.csockets[self.SENDER]
        csocket_n = context.csockets[self.PEER_NAME]
        connection = context.connection

        #INVOCATION PHASE
        # Receive bit of information
        xj = yield from csocket_s.recv()

        measurements = []
        for idx in range(self.m):

            q3= yield from teleport_recv(context=context, peer_name=self.SENDER)
            r3 = q3.measure()
            yield from connection.flush()
            measurements.append(int(r3))

        checkset = yield from csocket_s.recv()

        #CHECK PHASE
        T = math.ceil(self.mu * self.m)
        if len(checkset) >= T and all(measurements[i] != xj for i in checkset):
            y_inter = xj
        else:
            y_inter = None

        #CROSS-CALLING PHASE
        r0_output = yield from csocket_n.recv()
        r0_checkset = yield from csocket_n.recv()

        #CROSS-CHECK PHASE
        if r0_output != y_inter and r0_output is not None and y_inter is not None:
            if len(r0_checkset) >= T:
                n_opposite = sum(1 for i in r0_checkset if measurements[i] != r0_output)
                threshold = self.lam * T + len(r0_checkset) - T
                if n_opposite >= threshold:
                    y1 = r0_output
                else:
                    y1 = y_inter
            else:
                y1 = y_inter
        else:
            y1 = y_inter


        print(f"Node 2 result: {y1}")
        return {"y1": y1}