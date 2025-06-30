import tkinter as tk
from tkinter import ttk, scrolledtext

class DataItem:
    def __init__(self, name, initial_value):
        self.name = name
        self.value = initial_value
        self.reset_concurrency_state()

    def reset_concurrency_state(self):
        self.lock_owner = None
        self.lock_type = None
        self.waiting_queue = []
        self.read_timestamp = 0
        self.write_timestamp = 0

    def __repr__(self):
        return f"DataItem({self.name}, Value={self.value})"

class Transaction:
    def __init__(self, tid, operations_list, timestamp=None):
        self.id = tid
        self.operations = operations_list
        self.reset_state(timestamp)

    def reset_state(self, timestamp=None):
        self.state = "RUNNING"
        self.current_op_index = 0
        self.locks_held = []
        self.timestamp = timestamp if timestamp is not None else 0

    def __repr__(self):
        return f"Transaction({self.id}, State={self.state})"

class LockingConcurrencyManager:
    def __init__(self, data_items_dict, log_callback, message_counter_callback):
        self.data_items = data_items_dict
        self.log_message = log_callback
        self.update_message_count = message_counter_callback

    def acquire_lock(self, transaction, data_item, lock_type):
        self.log_message(f"T{transaction.id} requests {lock_type} lock on {data_item.name}.", "blue")
        self.update_message_count(1)

        if data_item.lock_owner is None:
            data_item.lock_owner = transaction.id
            data_item.lock_type = lock_type
            transaction.locks_held.append(data_item)
            transaction.state = "RUNNING"
            self.log_message(f"T{transaction.id} granted {lock_type} lock on {data_item.name}.", "green")
            self.update_message_count(1)
            return True
        elif data_item.lock_owner == transaction.id:
            if lock_type == 'S' and data_item.lock_type == 'X':
                self.log_message(f"T{transaction.id} already holds X lock on {data_item.name}. S request is compatible.", "green")
                return True
            elif lock_type == 'X' and data_item.lock_type == 'S':
                if not data_item.waiting_queue:
                    data_item.lock_type = 'X'
                    self.log_message(f"T{transaction.id} upgraded S lock to X lock on {data_item.name}.", "green")
                    self.update_message_count(1)
                    return True
                else:
                    self.log_message(f"T{transaction.id} cannot upgrade S to X on {data_item.name} (other transactions waiting).", "orange")
            elif lock_type == data_item.lock_type:
                self.log_message(f"T{transaction.id} already holds {lock_type} lock on {data_item.name}.", "green")
                return True
        else:
            is_compatible = False
            if data_item.lock_type == 'S' and lock_type == 'S':
                is_compatible = True
                self.log_message(f"T{transaction.id} also granted S lock on {data_item.name} (shared).", "green")
                self.update_message_count(1)
                transaction.locks_held.append(data_item)
                return True

            if not is_compatible:
                self.log_message(f"T{transaction.id} cannot get {lock_type} lock on {data_item.name}. T{data_item.lock_owner} holds {data_item.lock_type} lock. T{transaction.id} is WAITING.", "orange")
                if transaction.id not in data_item.waiting_queue:
                    data_item.waiting_queue.append(transaction.id)
                transaction.state = "WAITING"
                return False

        return False

    def release_lock(self, transaction, data_item):
        if data_item.lock_owner == transaction.id or (data_item.lock_type == 'S' and transaction.id in data_item.waiting_queue):
            if data_item.lock_owner == transaction.id:
                self.log_message(f"T{transaction.id} releases {data_item.lock_type} lock on {data_item.name}.", "green")
                self.update_message_count(1)
                data_item.lock_owner = None
                data_item.lock_type = None

            if data_item in transaction.locks_held:
                transaction.locks_held.remove(data_item)

            if data_item.waiting_queue:
                self.log_message(f"Lock on {data_item.name} is now free. Waiting transactions ({data_item.waiting_queue}) will re-attempt.", "green")

    def release_all_locks(self, transaction):
        for item in list(transaction.locks_held):
            self.release_lock(transaction, item)
        transaction.locks_held.clear()

    def process_operation(self, transaction, op_type, data_item, value=None):
        if op_type == 'read':
            if self.acquire_lock(transaction, data_item, 'S'):
                self.log_message(f"T{transaction.id} reads {data_item.name} (value: {data_item.value}).", "green")
                return True
            return False
        elif op_type == 'write':
            if self.acquire_lock(transaction, data_item, 'X'):
                data_item.value = value
                self.log_message(f"T{transaction.id} writes {value} to {data_item.name}.", "green")
                return True
            return False
        elif op_type == 'request_lock':
            if self.acquire_lock(transaction, data_item, value):
                self.log_message(f"T{transaction.id} explicitly acquired {value} lock on {data_item.name}.", "green")
                return True
            return False
        return False

    def commit_transaction(self, transaction):
        self.log_message(f"T{transaction.id} is COMMITTING.", "green")
        self.update_message_count(1)
        self.release_all_locks(transaction)
        transaction.state = "COMMITTED"
        self.log_message(f"T{transaction.id} COMMITTED successfully.", "green")

    def abort_transaction(self, transaction, reason):
        self.log_message(f"T{transaction.id} ABORTED (Reason: {reason}).", "red")
        self.update_message_count(1)
        self.release_all_locks(transaction)
        transaction.state = "ABORTED"
        for item in self.data_items.values():
            if transaction.id in item.waiting_queue:
                item.waiting_queue.remove(transaction.id)

    def detect_deadlock(self, all_transactions):
        waiting_transactions = [t for t in all_transactions if t.state == "WAITING"]
        if not waiting_transactions:
            return []

        wait_for_graph = {}

        for waiting_t in waiting_transactions:
            if waiting_t.current_op_index < len(waiting_t.operations):
                op_type, item_name, *_ = waiting_t.operations[waiting_t.current_op_index]
                data_item = self.data_items.get(item_name)

                if data_item and data_item.lock_owner and data_item.lock_owner != waiting_t.id:
                    if waiting_t.id not in wait_for_graph:
                        wait_for_graph[waiting_t.id] = []
                    wait_for_graph[waiting_t.id].append(data_item.lock_owner)
                elif data_item and waiting_t.id in data_item.waiting_queue and data_item.lock_owner is not None:
                    if waiting_t.id not in wait_for_graph:
                        wait_for_graph[waiting_t.id] = []
                    wait_for_graph[waiting_t.id].append(data_item.lock_owner)

        deadlocked_ids = []
        for t_id, waits_for_list in wait_for_graph.items():
            for waits_for_tid in waits_for_list:
                if waits_for_tid in wait_for_graph and t_id in wait_for_graph[waits_for_tid]:
                    if t_id not in deadlocked_ids:
                        deadlocked_ids.append(t_id)
                    if waits_for_tid not in deadlocked_ids:
                        deadlocked_ids.append(waits_for_tid)
        return deadlocked_ids

class TimestampConcurrencyManager:
    def __init__(self, data_items_dict, log_callback, message_counter_callback):
        self.data_items = data_items_dict
        self.log_message = log_callback
        self.update_message_count = message_counter_callback

    def process_operation(self, transaction, op_type, data_item, value=None):
        ts = transaction.timestamp

        if op_type == 'read':
            self.log_message(f"T{transaction.id} (TS={ts}) attempts to READ {data_item.name}.", "blue")
            self.update_message_count(1)

            if ts < data_item.write_timestamp:
                self.abort_transaction(transaction, f"Read Old Data (TS={ts} < WriteTS={data_item.write_timestamp})")
                return False
            else:
                data_item.read_timestamp = max(data_item.read_timestamp, ts)
                self.log_message(f"T{transaction.id} READS {data_item.name} (value: {data_item.value}). {data_item.name} ReadTS updated to {data_item.read_timestamp}.", "green")
                return True
        elif op_type == 'write':
            self.log_message(f"T{transaction.id} (TS={ts}) attempts to WRITE {value} to {data_item.name}.", "blue")
            self.update_message_count(1)

            if ts < data_item.read_timestamp or ts < data_item.write_timestamp:
                self.abort_transaction(transaction, f"Write Conflict (TS={ts} < ReadTS={data_item.read_timestamp} or WriteTS={data_item.write_timestamp})")
                return False
            else:
                data_item.value = value
                data_item.write_timestamp = ts
                self.log_message(f"T{transaction.id} WRITES {value} to {data_item.name}. {data_item.name} WriteTS updated to {data_item.write_timestamp}.", "green")
                return True
        return False

    def commit_transaction(self, transaction):
        self.log_message(f"T{transaction.id} is COMMITTING.", "green")
        self.update_message_count(1)
        transaction.state = "COMMITTED"
        self.log_message(f"T{transaction.id} COMMITTED successfully.", "green")

    def abort_transaction(self, transaction, reason):
        self.log_message(f"T{transaction.id} ABORTED (Reason: {reason}).", "red")
        self.update_message_count(1)
        transaction.state = "ABORTED"

class DDBMS_Simulator_GUI:
    def __init__(self, master):
        self.master = master
        master.title("DDBMS Concurrency Simulator")
        master.geometry("900x800")
        master.resizable(True, True)

        self.data_items = {}
        self.transactions_config = {}
        self.current_transactions = {}
        self.concurrency_manager = None
        self.current_mechanism = "locking"
        self.message_count = 0
        self.global_timestamp_counter = 0

        self.setup_simulation_scenarios()
        self.create_widgets()
        self.reset_simulation()

    def setup_simulation_scenarios(self):
        self.initial_data_items = {
            'X': 100,
            'Y': 200,
            'Z': 300
        }

        self.transactions_config['locking'] = [
            Transaction('T1', [('read', 'X'), ('write', 'Y', 150), ('read', 'Z')]),
            Transaction('T2', [('read', 'Y'), ('write', 'X', 250), ('read', 'Z')]),
            Transaction('T3', [('request_lock', 'X', 'X'), ('request_lock', 'Y', 'X')]),
            Transaction('T4', [('request_lock', 'Y', 'X'), ('request_lock', 'X', 'X')]),
            Transaction('T5', [('read', 'X'), ('write', 'X', 110)]),
        ]

        self.transactions_config['timestamping'] = [
            Transaction('T1', [('read', 'X'), ('write', 'Y', 150)]),
            Transaction('T2', [('read', 'Y'), ('write', 'X', 250)]),
            Transaction('T3', [('write', 'X', 500)]),
            Transaction('T4', [('read', 'X'), ('write', 'Y', 550)]),
            Transaction('T5', [('write', 'Y', 10)]),
            Transaction('T6', [('read', 'Y'), ('write', 'Z', 20)]),
            Transaction('T7', [('read', 'Y'), ('write', 'X', 70)]),
            Transaction('T8', [('write', 'Y', 80)]),
        ]

    def create_widgets(self):
        paned_window = ttk.PanedWindow(self.master, orient=tk.VERTICAL)
        paned_window.pack(fill=tk.BOTH, expand=True)

        control_frame = ttk.LabelFrame(paned_window, text="Simulation Controls")
        paned_window.add(control_frame)

        self.start_button = ttk.Button(control_frame, text="Start Simulation", command=self.start_simulation)
        self.start_button.pack(side="left", padx=5, pady=5)

        self.next_step_button = ttk.Button(control_frame, text="Next Step", command=self.next_step)
        self.next_step_button.pack(side="left", padx=5, pady=5)
        self.next_step_button.config(state="disabled")

        self.reset_button = ttk.Button(control_frame, text="Reset", command=self.reset_simulation)
        self.reset_button.pack(side="left", padx=5, pady=5)

        self.mechanism_var = tk.StringVar(value="locking")
        ttk.Radiobutton(control_frame, text="Locking", variable=self.mechanism_var, value="locking", command=self.select_mechanism).pack(side="left", padx=10)
        ttk.Radiobutton(control_frame, text="Timestamping", variable=self.mechanism_var, value="timestamping", command=self.select_mechanism).pack(side="left", padx=5)

        data_frame = ttk.LabelFrame(paned_window, text="Data Items Status")
        paned_window.add(data_frame)
        self.data_item_labels = {}
        for item_name in self.initial_data_items.keys():
            label = ttk.Label(data_frame, text="", font=("Helvetica", 10))
            label.pack(padx=5, pady=2, anchor="w")
            self.data_item_labels[item_name] = label

        transaction_frame = ttk.LabelFrame(paned_window, text="Transactions Status")
        paned_window.add(transaction_frame)

        transaction_canvas = tk.Canvas(transaction_frame)
        scrollbar = ttk.Scrollbar(transaction_frame, orient="vertical", command=transaction_canvas.yview)
        self.transaction_scrollable_frame = ttk.Frame(transaction_canvas)

        self.transaction_scrollable_frame.bind(
            "<Configure>",
            lambda e: transaction_canvas.configure(
                scrollregion=transaction_canvas.bbox("all")
            )
        )

        transaction_canvas.create_window((0, 0), window=self.transaction_scrollable_frame, anchor="nw")
        transaction_canvas.configure(yscrollcommand=scrollbar.set)

        transaction_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.transaction_labels = {}

        log_frame = ttk.LabelFrame(paned_window, text="Simulation Log")
        paned_window.add(log_frame)
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap="word", height=10, state="disabled", font=("Courier New", 9))
        self.log_text.pack(side="left", fill="both", expand=True)
        self.log_text.tag_config("green", foreground="green")
        self.log_text.tag_config("red", foreground="red")
        self.log_text.tag_config("blue", foreground="blue")
        self.log_text.tag_config("orange", foreground="orange")

        self.message_count_label = ttk.Label(self.master, text="Total Messages: 0", font=("Helvetica", 10, "bold"))
        self.message_count_label.pack(pady=5)

        help_label = ttk.Label(self.master, text="Use 'Start Simulation' to begin, 'Next Step' to proceed step-by-step, and 'Reset' to start over.", font=("Helvetica", 9, "italic"))
        help_label.pack(pady=5)

    def log_message(self, message, color="black"):
        self.log_text.config(state="normal")
        self.log_text.insert("end", message + "\n", color)
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def update_message_count(self, count=1):
        self.message_count += count
        self.message_count_label.config(text=f"Total Messages: {self.message_count}")

    def update_gui_status(self):
        for item_name, item in self.data_items.items():
            if self.current_mechanism == "locking":
                owner_info = f"Owner: {item.lock_owner if item.lock_owner else 'None'}, Type: {item.lock_type if item.lock_type else 'None'}"
                waiting_info = f"Waiting: {', '.join(item.waiting_queue)}" if item.waiting_queue else ""
                self.data_item_labels[item_name].config(text=f"{item_name}: Value={item.value}, {owner_info} {waiting_info}")
            else:
                ts_info = f"Read TS: {item.read_timestamp}, Write TS: {item.write_timestamp}"
                self.data_item_labels[item_name].config(text=f"{item_name}: Value={item.value}, {ts_info}")

        for t_id in self.transactions_config[self.current_mechanism]:
            if t_id.id not in self.transaction_labels:
                label = ttk.Label(self.transaction_scrollable_frame, text="", font=("Helvetica", 10))
                label.pack(padx=5, pady=2, anchor="w")
                self.transaction_labels[t_id.id] = label

            transaction = self.current_transactions.get(t_id.id)
            if transaction:
                op_info = ""
                if transaction.state == "RUNNING" and transaction.current_op_index < len(transaction.operations):
                    current_op = transaction.operations[transaction.current_op_index]
                    op_info = f"Next Op: {current_op[0]} {current_op[1]}"

                ts_display = f"TS={transaction.timestamp}" if self.current_mechanism == "timestamping" else ""
                self.transaction_labels[t_id.id].config(text=f"{transaction.id}: State={transaction.state} {ts_display} {op_info}")

                if transaction.state == "COMMITTED":
                    self.transaction_labels[t_id.id].config(foreground="green")
                elif transaction.state == "ABORTED":
                    self.transaction_labels[t_id.id].config(foreground="red")
                elif transaction.state == "WAITING":
                    self.transaction_labels[t_id.id].config(foreground="orange")
                else:
                    self.transaction_labels[t_id.id].config(foreground="black")
            else:
                self.transaction_labels[t_id.id].config(text="", foreground="black")

    def select_mechanism(self):
        new_mechanism = self.mechanism_var.get()
        if self.current_mechanism != new_mechanism:
            self.current_mechanism = new_mechanism
            self.reset_simulation()
            self.log_message(f"Concurrency mechanism set to: {self.current_mechanism.upper()}", "blue")

    def reset_simulation(self):
        self.log_text.config(state="normal")
        self.log_text.delete(1.0, "end")
        self.log_text.config(state="disabled")

        self.message_count = 0
        self.update_message_count(0)
        self.global_timestamp_counter = 0

        self.start_button.config(state="normal")
        self.next_step_button.config(state="disabled")

        self.data_items.clear()
        for name, value in self.initial_data_items.items():
            item = DataItem(name, value)
            self.data_items[name] = item

        self.current_transactions.clear()

        for label_id in list(self.transaction_labels.keys()):
            self.transaction_labels[label_id].destroy()
        self.transaction_labels.clear()

        self.update_gui_status()
        self.log_message("Simulation reset. Select a mechanism and click 'Start Simulation'.", "blue")

    def start_simulation(self):
        self.log_message(f"Starting simulation with {self.current_mechanism.upper()} mechanism...", "blue")
        self.start_button.config(state="disabled")
        self.next_step_button.config(state="normal")
        self.message_count = 0
        self.update_message_count(0)
        self.global_timestamp_counter = 0

        for item in self.data_items.values():
            item.reset_concurrency_state()

        self.current_transactions.clear()
        self.active_transactions_queue = []

        for t_config_template in self.transactions_config[self.current_mechanism]:
            self.global_timestamp_counter += 1
            new_t = Transaction(t_config_template.id, list(t_config_template.operations), self.global_timestamp_counter)
            new_t.reset_state(self.global_timestamp_counter)

            self.current_transactions[new_t.id] = new_t
            self.active_transactions_queue.append(new_t)

            if new_t.id not in self.transaction_labels:
                label = ttk.Label(self.transaction_scrollable_frame, text="", font=("Helvetica", 10))
                label.pack(padx=5, pady=2, anchor="w")
                self.transaction_labels[new_t.id] = label
            else:
                self.transaction_labels[new_t.id].config(text="", foreground="black")

        if self.current_mechanism == "locking":
            self.concurrency_manager = LockingConcurrencyManager(self.data_items, self.log_message, self.update_message_count)
        else:
            self.concurrency_manager = TimestampConcurrencyManager(self.data_items, self.log_message, self.update_message_count)

        self.update_gui_status()
        self.log_message("Simulation ready. Click 'Next Step' to advance through operations.", "green")

    def next_step(self):
        self.active_transactions_queue = [t for t in self.active_transactions_queue if t.state not in ["COMMITTED", "ABORTED"]]

        if not self.active_transactions_queue:
            self.log_message("All transactions have completed or aborted. Simulation finished.", "green")
            self.next_step_button.config(state="disabled")
            return

        current_t = self.active_transactions_queue.pop(0)

        if current_t.current_op_index >= len(current_t.operations):
            self.log_message(f"T{current_t.id}: All operations processed. Attempting COMMIT.", "blue")
            self.concurrency_manager.commit_transaction(current_t)
            self.update_gui_status()
            return

        op_type, item_name, *value_arg = current_t.operations[current_t.current_op_index]
        data_item = self.data_items.get(item_name)

        if not data_item:
            self.concurrency_manager.abort_transaction(current_t, f"Data item {item_name} not found for {current_t.id}.")
            self.update_gui_status()
            return

        op_succeeded = self.concurrency_manager.process_operation(
            current_t, op_type, data_item, value_arg[0] if value_arg else None
        )

        if op_succeeded:
            current_t.current_op_index += 1
            self.active_transactions_queue.append(current_t)
        else:
            if current_t.state == "WAITING":
                self.active_transactions_queue.append(current_t)

        if self.current_mechanism == "locking":
            deadlocked_t_ids = self.concurrency_manager.detect_deadlock(list(self.current_transactions.values()))
            if deadlocked_t_ids:
                self.log_message(f"\n{'*' * 30}\n!!! DEADLOCK DETECTED involving: {', '.join(deadlocked_t_ids)} !!!\n{'*' * 30}\n", "red")
                for tid_in_deadlock in deadlocked_t_ids:
                    t_to_abort = self.current_transactions.get(tid_in_deadlock)
                    if t_to_abort and t_to_abort.state == "WAITING":
                        self.concurrency_manager.abort_transaction(t_to_abort, "Deadlock Resolution")
                self.active_transactions_queue = [t for t in self.active_transactions_queue if t.state not in ["COMMITTED", "ABORTED"]]

        self.update_gui_status()

if __name__ == "__main__":
    root = tk.Tk()
    app = DDBMS_Simulator_GUI(root)
    root.mainloop()
