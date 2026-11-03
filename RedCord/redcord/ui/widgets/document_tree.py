from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem


class DocumentTreeWidget(QTreeWidget):
    def __init__(self):
        super().__init__()
        self.setHeaderLabels(["Projects / Documents"])

    def load_sample(self):
        root = QTreeWidgetItem(["Demo Project"])
        root.addChild(QTreeWidgetItem(["Character: Aeryn"]))
        root.addChild(QTreeWidgetItem(["Chapter: Prologue"]))
        self.addTopLevelItem(root)
        root.setExpanded(True)
