import sys
import time
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import pyvisa as visa

psu_min_voltage = 0  # V
psu_max_voltage = 8  # V
psu_current_limit = 0.04  # A
voltage_increment = 1
accuracy = 2

close_psu_on_gui_close = False

voltage_factor = pow(10, accuracy)

psu_ips = {
    1: {'ip_address': '192.168.0.120', 'channel': None, 'model': 'keysight'},
    2: {'ip_address': '192.168.0.114', 'channel': '1', 'model': 'rigol'},
    3: {'ip_address': '192.168.0.114', 'channel': '2', 'model': 'rigol'},
    4: {'ip_address': '192.168.0.122', 'channel': None, 'model': 'keysight'}
}

# Slider Title, Minimum Value, Maximum Value, Starting Value
sliders_info = [
    (f'<b>Driver 1 bias: 0V</b>', psu_min_voltage, psu_max_voltage, 0),
    (f'<b>Driver 2 bias: 0V</b>', psu_min_voltage, psu_max_voltage, 0),
    (f'<b>Driver 3 bias: 0V</b>', psu_min_voltage, psu_max_voltage, 0),
    (f'<b>Driver 4 bias: 0V</b>', psu_min_voltage, psu_max_voltage, 0)
]

rm = visa.ResourceManager()

PSU_1 = rm.open_resource(f'TCPIP0::{psu_ips[1]["ip_address"]}::inst0::INSTR')
PSU_2 = rm.open_resource(f'TCPIP0::{psu_ips[2]["ip_address"]}::inst0::INSTR')
PSU_3 = rm.open_resource(f'TCPIP0::{psu_ips[4]["ip_address"]}::inst0::INSTR')


def get_correct_PSU(psu_id):
    PSU = None
    if psu_id == 1:
        PSU = PSU_1
    elif psu_id == 2 or psu_id == 3:
        PSU = PSU_2
    elif psu_id == 4:
        PSU = PSU_3
    return PSU


def initialize_psu(psu_id, value):
    PSU = get_correct_PSU(psu_id)

    if psu_ips[psu_id]['model'] == 'keysight':
        PSU.write(':SOUR:FUNC:MODE VOLT')
        PSU.write(f':SENS:CURR:PROT {psu_current_limit}')
        PSU.write(':OUTP OFF')
    else:
        PSU.write(f':OUTPut:OVP:VAL CH{psu_ips[psu_id]["channel"]}, 1')
        PSU.write(f':OUTPut:OVP CH{psu_ips[psu_id]["channel"]}, ON')
        PSU.write(f'SOUR{psu_ips[psu_id]["channel"]}:CURR {psu_current_limit}')
        PSU.write(f'SOUR{psu_ips[psu_id]["channel"]}:VOLT {value / voltage_factor}')
        PSU.write(f':OUTP CH{psu_ips[psu_id]["channel"]}, OFF')

    print(f'PSU ID {psu_id} -> Initialized')


def control_psu(psu_id, value, reverse_bias):
    PSU = get_correct_PSU(psu_id)

    if psu_ips[psu_id]['model'] == 'keysight':
        if value == 0:
            PSU.write(f':SOUR:VOLT 0')
            PSU.write(':OUTP OFF')
        else:
            if reverse_bias:
                PSU.write(f':SOUR:VOLT -{value / voltage_factor}')
                PSU.write(':OUTP ON')
            else:
                PSU.write(f':SOUR:VOLT {value / voltage_factor}')
                PSU.write(':OUTP ON')
    else:
        if value == 0:
            PSU.write(f'SOUR{psu_ips[psu_id]["channel"]}:VOLT 0')
            PSU.write(f':OUTP CH{psu_ips[psu_id]["channel"]}, OFF')
        else:
            PSU.write(f'SOUR{psu_ips[psu_id]["channel"]}:VOLT {value / voltage_factor}')
            PSU.write(f':OUTP CH{psu_ips[psu_id]["channel"]}, ON')


class AppInterface(QWidget):
    def __init__(self):
        super().__init__()

        # Initialize parameters
        self.slider_labels = None
        self.reverse_checkboxes = None
        self.sliders = None
        self.plus_buttons = None
        self.minus_buttons = None
        self.max_input_field = None
        self.confirm_button = None

        self.init_ui()

    def init_ui(self):
        self.slider_labels = []
        self.reverse_checkboxes = []
        self.sliders = []
        self.plus_buttons = []
        self.minus_buttons = []

        self.setWindowTitle('Driver Biases')
        self.setGeometry(100, 100, 350, 400)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)  # Set spacing between layouts
        self.setLayout(main_layout)

        i = 1
        for title, min_val, max_val, init_val in sliders_info:
            slider_title_layout = QHBoxLayout()

            slider_label = QLabel(title, self)
            slider_label.setAlignment(Qt.AlignCenter)  # Align text in the center
            slider_title_layout.addWidget(slider_label)

            slider_label.setEnabled(False)
            self.slider_labels.append(slider_label)

            checkbox = QCheckBox('Reverse Bias')
            checkbox.stateChanged.connect(lambda value, s_label=slider_label, s_id=i: self.toggle_reverse_bias(s_label, s_id))
            slider_title_layout.addWidget(checkbox)

            checkbox.setEnabled(False)
            if psu_ips[i]['model'] != 'keysight':
                checkbox.setVisible(False)
            self.reverse_checkboxes.append(checkbox)

            slider_value_control_layout = QHBoxLayout()
            slider = QSlider(Qt.Horizontal, self)  # Set orientation to horizontal

            slider.setMinimum(min_val * voltage_factor)
            slider.setMaximum(max_val * voltage_factor)
            slider.setValue(int(init_val) * voltage_factor)
            initialize_psu(i, int(init_val))
            slider.setTickPosition(QSlider.TicksBelow)
            slider.setTickInterval(voltage_factor)
            slider.valueChanged.connect(lambda value, s_label=slider_label, s_id=i: self.update_slider_value(s_label, s_id, value, 'slider'))
            slider_value_control_layout.addWidget(slider)

            slider.setEnabled(False)
            self.sliders.append(slider)

            plus_button = QPushButton('+', self)
            plus_button.setFixedSize(40, 40)  # Square buttons
            plus_button.clicked.connect(lambda value, s_label=slider_label, s_id=i, s=slider: self.update_slider_value(s_label, s_id, s.value() + voltage_increment, 'button'))
            slider_value_control_layout.addWidget(plus_button)

            plus_button.setEnabled(False)
            self.plus_buttons.append(plus_button)

            minus_button = QPushButton('-', self)
            minus_button.setFixedSize(40, 40)  # Square buttons

            minus_button.clicked.connect(lambda value, s_label=slider_label, s_id=i, s=slider: self.update_slider_value(s_label, s_id, s.value() - voltage_increment, 'button'))
            slider_value_control_layout.addWidget(minus_button)

            minus_button.setEnabled(False)
            self.minus_buttons.append(minus_button)

            main_layout.addLayout(slider_title_layout)
            main_layout.addLayout(slider_value_control_layout)

            i += 1

        # Text input field and confirm button
        limits_layout = QHBoxLayout()

        # Add label and text input field
        label = QLabel(f'<b>Maximum value (Limit: {psu_max_voltage}V)</b>', self)
        label.setAlignment(Qt.AlignCenter)  # Align text in the center
        limits_layout.addWidget(label)

        self.max_input_field = QLineEdit(self)
        limits_layout.addWidget(self.max_input_field)

        self.confirm_button = QPushButton('Confirm', self)
        self.confirm_button.clicked.connect(self.confirm_button_clicked)

        limits_layout.addWidget(self.confirm_button)

        main_layout.addLayout(limits_layout)

        # Connect returnPressed signal of text input to click signal of button
        self.max_input_field.returnPressed.connect(self.confirm_button.click)

        self.show()

    def update_slider_value(self, label, slider_id, value, mode):
        if mode == 'button':
            self.sliders[slider_id - 1].setValue(value)
            self.sliders[slider_id - 1].setValue(value)
        reverse_bias = self.reverse_checkboxes[slider_id - 1].isChecked()
        if reverse_bias:
            label.setText(f'<b>{label.text().split(":")[0]}: -{value / voltage_factor}V</b>')
        else:
            label.setText(f'<b>{label.text().split(":")[0]}: {value / voltage_factor}V</b>')
        control_psu(slider_id, value, reverse_bias)

    def toggle_reverse_bias(self, label, slider_id):
        psu_id = slider_id
        PSU = get_correct_PSU(psu_id)
        if psu_ips[psu_id]['model'] == 'keysight':
            PSU.write(f':SOUR:VOLT 0')
            PSU.write(':OUTP OFF')
        else:
            PSU.write(f'SOUR{psu_ips[psu_id]["channel"]}:VOLT 0')
            PSU.write(f':OUTP CH{psu_ips[psu_id]["channel"]}, OFF')
        self.sliders[slider_id - 1].setValue(0)
        label.setText(f'<b>{label.text().split(":")[0]}: 0V</b>')

    def confirm_button_clicked(self):
        timer = QTimer(self)
        max_value = self.max_input_field.text()
        psu_id = 1
        accept = False
        for slider in self.sliders:
            if max_value and float(max_value) <= psu_max_voltage:
                slider.setMaximum(int(float(max_value) * voltage_factor))
                if psu_ips[psu_id]['model'] != 'keysight':
                    PSU = get_correct_PSU(psu_id)
                    PSU.write(f':OUTPut:OVP:VAL CH{psu_ips[psu_id]["channel"]}, {float(max_value) + 0.1}')
                # Change button background color to green
                self.confirm_button.setStyleSheet('background-color: #90EE90')
                timer.singleShot(500, self.reset_button_color)
                accept = True
            psu_id += 1
        if accept:
            for slider_label in self.slider_labels:
                slider_label.setEnabled(True)
            for checkbox in self.reverse_checkboxes:
                checkbox.setEnabled(True)
            for slider in self.sliders:
                slider.setEnabled(True)
            for plus_button in self.plus_buttons:
                plus_button.setEnabled(True)
            for minus_button in self.minus_buttons:
                minus_button.setEnabled(True)

    def reset_button_color(self):
        # Revert button background color to default
        self.confirm_button.setStyleSheet('')

    def closeEvent(self, event, **kwargs):
        # Perform cleanup or other actions when the window is closed
        if close_psu_on_gui_close:
            PSU_1.write(':OUTP OFF')
            PSU_2.write(f':OUTP CH1, OFF')
            PSU_2.write(f':OUTP CH2, OFF')
            PSU_3.write(':OUTP OFF')
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = AppInterface()
    sys.exit(app.exec_())
