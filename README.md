# ![](resources/nocomponentwarn/32x32.png) NoComponentWarn

A Fusion 360 add-in that warns when features are created outside components. It also warns when creating feature across components (It works if the reference feature is selected before creating the new feature).

A warning will be shown every time a new feature is created at the top-level or in the wrong component. At that point, the user can choose to either Cancel, Continue or Stop the warning messages for the current document session.

Currently Windows-only.



![Screenshot](screenshot.png)



## Installation
Download the add-in from the [Releases](https://github.com/thomasa88/NoComponentWarn/releases) page.

Unpack it into `API\AddIns` (see [How to install an add-in or script in Fusion 360](https://knowledge.autodesk.com/support/fusion-360/troubleshooting/caas/sfdcarticles/sfdcarticles/How-to-install-an-ADD-IN-and-Script-in-Fusion-360.html)).

Make sure the directory is named `NoComponentWarn`, with no suffix.

## Usage

A warning will be shown every time a new feature is created at the top-level or in the wrong component.

At that point, the following choices are given:

* *Cancel* (Esc): Cancel the operation
* *Continue* (Enter): Go through with the operation and create the feature
* *Stop warning*: Go through with the operation and stop warning for this document for this session.

The add-in can be temporarily disabled using the *Scripts and Add-ins* dialog. Press *Shift+S* in Fusion 360™ and go to the *Add-Ins* tab.

## Author

This add-in is created by Thomas Axelsson.

## License

This project is licensed under the terms of the MIT license. See [LICENSE](LICENSE).

## Changelog

* v 1.0.2
  * Enable *Run on Startup* by default.
* v 1.0.1
  * Fix: Don't warn when creating a solid feature from sketch face while in the sketch.
* v 1.0.0
  * Warn when creating features in the wrong component.
* v 0.2.6
  * Fix: Make "Run on start-up" work
* v 0.2.5
  * Fix: Don't double-trigger when sketch is created using button
* v 0.2.4
  * Fix: Match all plane commands
* v 0.2.3
  * Warn on construction object creation as well
  * More detailed usage instructions
* v 0.2.2
  * MIT license, for inclusion Autodesk app store
* v 0.2.1
  * Fix duplicated words in dialog text
* v 0.2.0
  * Better button labels