# Source this before building the Android app:  . tools/env.sh
# Everything lives in ~/toolchain and was installed without root.
export JAVA_HOME="$HOME/toolchain/jdk21"          # Capacitor 7 needs JDK 21, not 17
export ANDROID_HOME="$HOME/toolchain/android-sdk"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"
[ -s "$HOME/.nvm/nvm.sh" ] && . "$HOME/.nvm/nvm.sh"
