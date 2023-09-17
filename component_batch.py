import sys
import aqt.qt

from typing import List, Optional

component_common = __import__('component_common', globals(), locals(), [], sys._addon_import_level_base)
component_source = __import__('component_source', globals(), locals(), [], sys._addon_import_level_base)
component_target = __import__('component_target', globals(), locals(), [], sys._addon_import_level_base)
component_voiceselection = __import__('component_voiceselection', globals(), locals(), [], sys._addon_import_level_base)
component_text_processing = __import__('component_text_processing', globals(), locals(), [], sys._addon_import_level_base)
component_batch_preview = __import__('component_batch_preview', globals(), locals(), [], sys._addon_import_level_base)
component_label_preview = __import__('component_label_preview', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_base)
gui_utils = __import__('gui_utils', globals(), locals(), [], sys._addon_import_level_base)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_base)
logger = logging_utils.get_child_logger(__name__)


class ComponentBatch(component_common.ConfigComponentBase):
    MIN_WIDTH_COMPONENT = 600
    MIN_HEIGHT = 250

    def __init__(self, hypertts, dialog):
        self.hypertts = hypertts
        self.dialog = dialog
        self.batch_model = config_models.BatchConfig(self.hypertts.anki_utils)
        self.note = None

        # create certain widgets upfront
        self.profile_name_label = aqt.qt.QLabel()
        self.show_settings_button = aqt.qt.QPushButton('Hide Settings')
        self.preview_sound_button = aqt.qt.QPushButton('Preview Sound')
        self.apply_button = aqt.qt.QPushButton('Apply to Notes')
        self.cancel_button = aqt.qt.QPushButton('Cancel')
        self.profile_load_button = aqt.qt.QPushButton('Load')
        self.profile_save_button = aqt.qt.QPushButton('Save')

    def configure_browser(self, note_id_list):
        self.note_id_list = note_id_list
        field_list = self.hypertts.get_all_fields_from_notes(note_id_list)
        if len(field_list) == 0:
            raise Exception(f'could not find any fields in the selected {len(note_id_list)} notes')
        self.source = component_source.BatchSource(self.hypertts, field_list, self.source_model_updated)
        self.target = component_target.BatchTarget(self.hypertts, field_list, self.target_model_updated)
        self.voice_selection = component_voiceselection.VoiceSelection(self.hypertts, self.dialog, self.voice_selection_model_updated)
        self.text_processing = component_text_processing.TextProcessing(self.hypertts, self.text_processing_model_updated)
        self.preview = component_batch_preview.BatchPreview(self.hypertts, self.note_id_list, 
            self.sample_selected, self.apply_notes_batch_start, self.apply_notes_batch_end)
        self.editor_mode = False
        self.show_settings = True

    def configure_editor(self, note, editor, add_mode):
        self.note = note
        self.editor = editor
        self.add_mode = add_mode
        field_list = list(self.note.keys())
        self.source = component_source.BatchSource(self.hypertts, field_list, self.source_model_updated)
        self.target = component_target.BatchTarget(self.hypertts, field_list, self.target_model_updated)
        self.voice_selection = component_voiceselection.VoiceSelection(self.hypertts, self.dialog, self.voice_selection_model_updated)
        self.text_processing = component_text_processing.TextProcessing(self.hypertts, self.text_processing_model_updated)
        self.preview = component_label_preview.LabelPreview(self.hypertts, note)
        self.editor_mode = True

    def new_preset(self, preset_name):
        """start with a new preset"""
        self.batch_model = config_models.BatchConfig(self.hypertts.anki_utils)
        self.batch_model.name = preset_name
        self.profile_name_label.setText(preset_name)
        self.disable_load_profile_button('Load')
        self.enable_save_profile_button()

    def load_preset(self, preset_id):
        model = self.hypertts.load_preset(preset_id)
        self.load_model(model)
        # disable load/save buttons
        self.disable_load_profile_button('Loaded')
        self.disable_save_profile_button('Save')

    def load_model(self, model):
        logger.info('load_model')
        self.batch_model = model
        # disseminate to all components
        self.profile_name_label.setText(model.name)
        self.source.load_model(model.source)
        self.target.load_model(model.target)
        self.voice_selection.load_model(model.voice_selection)
        self.text_processing.load_model(model.text_processing)
        self.preview.load_model(self.batch_model)

    def get_model(self):
        return self.batch_model

    def source_model_updated(self, model):
        logger.info(f'source_model_updated: {model}')
        self.batch_model.set_source(model)
        self.model_part_updated_common()

    def target_model_updated(self, model):
        logger.info('target_model_updated')
        self.batch_model.set_target(model)
        self.model_part_updated_common()

    def voice_selection_model_updated(self, model):
        logger.info('voice_selection_model_updated')
        self.batch_model.set_voice_selection(model)
        self.model_part_updated_common()

    def text_processing_model_updated(self, model):
        logger.info('text_processing_model_updated')
        self.batch_model.text_processing = model
        self.model_part_updated_common()

    def model_part_updated_common(self):
        self.preview.load_model(self.batch_model)
        # are we in editor mode ? if so, set the sample text on the voice component
        if self.note != None:
            if self.batch_model.source != None and self.batch_model.text_processing != None:
                try:
                    source_text, processed_text = self.hypertts.get_source_processed_text(self.note, self.batch_model.source, self.batch_model.text_processing)
                    self.voice_selection.sample_text_selected(processed_text)
                except Exception as e:
                    logger.warning(f'could not set sample text: {e}')
        self.enable_save_profile_button()

    def enable_save_profile_button(self):
        logger.info('enable_save_profile_button')
        self.profile_save_button.setEnabled(True)
        self.profile_save_button.setStyleSheet(self.hypertts.anki_utils.get_green_stylesheet())
        self.profile_save_button.setText('Save')

    def disable_save_profile_button(self, text):
        logger.info('disable_save_profile_button')
        self.profile_save_button.setEnabled(False)
        self.profile_save_button.setStyleSheet(None)
        self.profile_save_button.setText(text)

    def enable_load_profile_button(self):
        self.profile_load_button.setEnabled(True)
        self.profile_load_button.setStyleSheet(self.hypertts.anki_utils.get_green_stylesheet())
        self.profile_load_button.setText('Load')

    def disable_load_profile_button(self, text):
        self.profile_load_button.setEnabled(False)
        self.profile_load_button.setStyleSheet(None)
        self.profile_load_button.setText(text)

    def sample_selected(self, note_id, text):
        self.voice_selection.sample_text_selected(text)
        self.note = self.hypertts.anki_utils.get_note_by_id(note_id)
        self.preview_sound_button.setEnabled(True)
        self.preview_sound_button.setText('Preview Sound')

    def draw(self, layout):
        self.vlayout = aqt.qt.QVBoxLayout()

        # profile management
        # ==================

        hlayout = aqt.qt.QHBoxLayout()
        hlayout.addWidget(aqt.qt.QLabel('Preset:'))

        font = aqt.qt.QFont()
        font.setBold(True)
        self.profile_name_label.setFont(font)

        hlayout.addWidget(self.profile_name_label)

        self.disable_load_profile_button('Load')
        hlayout.addWidget(self.profile_load_button)
        self.disable_save_profile_button('Save')
        hlayout.addWidget(self.profile_save_button)

        self.profile_delete_button = aqt.qt.QPushButton('Delete')
        hlayout.addWidget(self.profile_delete_button)

        hlayout.addStretch()
        # logo header
        hlayout.addLayout(gui_utils.get_hypertts_label_header(self.hypertts.hypertts_pro_enabled()))
        self.vlayout.addLayout(hlayout)

        self.profile_load_button.pressed.connect(self.load_profile_button_pressed)
        self.profile_save_button.pressed.connect(self.save_profile_button_pressed)
        self.profile_delete_button.pressed.connect(self.delete_profile_button_pressed)

        # preset settings tabs
        # ====================

        self.tabs = aqt.qt.QTabWidget()

        self.tabs.addTab(self.source.draw(), 'Source')
        self.tabs.addTab(self.target.draw(), 'Target')
        self.tabs.addTab(self.voice_selection.draw(), 'Voice Selection')
        self.tabs.addTab(self.text_processing.draw(), 'Text Processing')

        if self.editor_mode == False:
            self.splitter = aqt.qt.QSplitter(aqt.qt.Qt.Orientation.Horizontal)
            self.splitter.addWidget(self.tabs)

            self.preview_widget = aqt.qt.QWidget()
            self.preview_widget.setLayout(self.preview.draw())
            self.splitter.addWidget(self.preview_widget)
            self.vlayout.addWidget(self.splitter, 1) # splitter is what should stretch
        else:
            self.vlayout.addWidget(self.tabs, 1) # the tabs should stretch
            self.preview_widget = aqt.qt.QWidget()
            self.preview_widget.setLayout(self.preview.draw())            
            self.vlayout.addWidget(self.preview_widget)


        # setup bottom buttons
        # ====================

        hlayout = aqt.qt.QHBoxLayout()
        hlayout.addStretch()

        # show settings button
        if not self.editor_mode:
            hlayout.addWidget(self.show_settings_button)
        # preview button
        if not self.editor_mode:
            self.preview_sound_button.setText('Select Note to Preview Sound')
            self.preview_sound_button.setEnabled(False)
        hlayout.addWidget(self.preview_sound_button)
        # apply button
        apply_label_text = 'Apply To Notes'
        if self.editor_mode:
            apply_label_text = 'Apply To Note'
        self.apply_button.setText(apply_label_text)
        self.apply_button.setStyleSheet(self.hypertts.anki_utils.get_green_stylesheet())
        hlayout.addWidget(self.apply_button)
        # cancel button
        self.cancel_button.setStyleSheet(self.hypertts.anki_utils.get_red_stylesheet())
        hlayout.addWidget(self.cancel_button)
        self.vlayout.addLayout(hlayout)

        self.show_settings_button.pressed.connect(self.show_settings_button_pressed)
        self.preview_sound_button.pressed.connect(self.sound_preview_button_pressed)
        self.apply_button.pressed.connect(self.apply_button_pressed)
        self.cancel_button.pressed.connect(self.cancel_button_pressed)

        self.cancel_button.setFocus()

        layout.addLayout(self.vlayout)

    def get_min_size(self):
        return self.MIN_HEIGHT

    def no_settings_editor(self):
        # when launched from the editor
        self.dialog.setMinimumSize(self.MIN_WIDTH_COMPONENT, self.get_min_size())

    def collapse_settings(self):
        # when we have already loaded a batch
        self.splitter.setSizes([0, self.MIN_WIDTH_COMPONENT])
        self.dialog.setMinimumSize(self.MIN_WIDTH_COMPONENT, self.get_min_size())
        self.show_settings = False
        self.show_settings_button.setText('Show Settings')

    def display_settings(self):
        # when configuring a new batch
        self.splitter.setSizes([self.MIN_WIDTH_COMPONENT, self.MIN_WIDTH_COMPONENT])
        self.dialog.setMinimumSize(self.MIN_WIDTH_COMPONENT * 2, self.get_min_size())
        self.show_settings = True
        self.show_settings_button.setText('Hide Settings')

    def load_profile_button_pressed(self):
        with self.hypertts.error_manager.get_single_action_context('Loading Preset'):
            profile_name = self.profile_name_combobox.currentText()
            self.load_model(self.hypertts.load_batch_config(profile_name))
            self.disable_load_profile_button('Preset Loaded')
            self.disable_save_profile_button('Save')

    def save_profile_button_pressed(self):
        with self.hypertts.error_manager.get_single_action_context('Saving Preset'):
            profile_name = self.profile_name_combobox.currentText()
            self.hypertts.save_batch_config(profile_name, self.get_model())
            self.disable_save_profile_button('Preset Saved')
            self.disable_load_profile_button('Load')

    def delete_profile_button_pressed(self):
        profile_name = self.profile_name_combobox.currentText()
        proceed = self.hypertts.anki_utils.ask_user(f'Delete Preset {profile_name} ?', self.dialog)
        if proceed == True:
            with self.hypertts.error_manager.get_single_action_context('Deleting Preset'):
                self.hypertts.delete_batch_config(profile_name)
                self.refresh_profile_combobox()

    def show_settings_button_pressed(self):
        if self.show_settings:
            self.collapse_settings()
        else:
            self.display_settings()

    def sound_preview_button_pressed(self):
        self.disable_bottom_buttons()
        self.preview_sound_button.setText('Playing Preview...')
        self.hypertts.anki_utils.run_in_background(self.sound_preview_task, self.sound_preview_task_done)

    def apply_button_pressed(self):
        with self.hypertts.error_manager.get_single_action_context('Applying Audio to Notes'):
            self.get_model().validate()
            logger.info('apply_button_pressed')
            if self.editor_mode:
                self.disable_bottom_buttons()
                self.apply_button.setText('Loading...')
                self.hypertts.anki_utils.run_in_background(self.apply_note_editor_task, self.apply_note_editor_task_done)
            else:
                self.disable_bottom_buttons()
                self.apply_button.setText('Loading...')
                self.preview.apply_audio_to_notes()

    def cancel_button_pressed(self):
        self.dialog.close()

    def apply_note_editor_task(self):
        logger.debug('apply_note_editor_task')
        self.hypertts.editor_note_add_audio(self.batch_model, self.editor, self.note, self.add_mode, None)
        return True

    def apply_note_editor_task_done(self, result):
        logger.debug('apply_note_editor_task_done')
        with self.hypertts.error_manager.get_single_action_context('Adding Audio to Note'):
            result = result.result()
            self.dialog.close()
        self.hypertts.anki_utils.run_on_main(self.finish_apply_note_editor)
    
    def finish_apply_note_editor(self):
        self.enable_bottom_buttons()
        self.apply_button.setText('Apply To Note')

    def sound_preview_task(self):
        if self.note == None:
            raise errors.NoNotesSelectedPreview()
        self.hypertts.preview_note_audio(self.batch_model, self.note, None)
        return True

    def sound_preview_task_done(self, result):
        with self.hypertts.error_manager.get_single_action_context('Playing Sound Preview'):
            result = result.result()
        self.hypertts.anki_utils.run_on_main(self.finish_sound_preview)

    def finish_sound_preview(self):
        self.enable_bottom_buttons()
        self.preview_sound_button.setText('Preview Sound')

    def disable_bottom_buttons(self):
        self.preview_sound_button.setEnabled(False)
        self.apply_button.setEnabled(False)
        self.cancel_button.setEnabled(False)

    def enable_bottom_buttons(self):
        self.preview_sound_button.setEnabled(True)
        self.apply_button.setEnabled(True)
        self.cancel_button.setEnabled(True)

    def apply_notes_batch_start(self):
        pass

    def batch_interrupted_button_setup(self):
        self.enable_bottom_buttons()
        self.apply_button.setText('Apply To Notes')

    def batch_completed_button_setup(self):
        self.cancel_button.setText('Close')
        self.cancel_button.setStyleSheet(self.hypertts.anki_utils.get_green_stylesheet())
        self.cancel_button.setEnabled(True)
        self.apply_button.setStyleSheet(None)
        self.apply_button.setText('Done')

    def apply_notes_batch_end(self, completed):
        if completed:
            self.hypertts.anki_utils.run_on_main(self.batch_completed_button_setup)
        else:
            self.hypertts.anki_utils.run_on_main(self.batch_interrupted_button_setup)

        