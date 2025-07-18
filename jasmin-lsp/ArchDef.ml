
module Arch =
  ( val let use_set0 = true and use_lea = false in
        let call_conv = Jasmin.Glob_options.Linux in
        let module C : Jasmin.Arch_full.Core_arch =
          (val Jasmin.CoreArchFactory.core_arch_x86 ~use_lea ~use_set0 call_conv)
        in
        (module Jasmin.Arch_full.Arch_from_Core_arch (C) : Jasmin.Arch_full.Arch) )
