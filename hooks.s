// Ocarina of Time (0400486024DEC000, main build e0f3ccfaf50065ae4ea01eb5aeb13b1a): menus confirm with the
// bottom face button and cancel with the right one, gameplay keeps Nintendo positions (play with DM_PAD_STYLE=switch).
// Linked by build_mod.py at PATCH_BASE in main.patched.bin; the words marked FIX_* are filled there.
// State page (RW, unused gap between the frame-step page and the patch area): STATE+0 = u32 frame number of the last
// frame a menu screen had a focused button, STATE+4 = u32 frame number (counted by the first npad controller's calc);
// STATE+0x40.. = 16 slots {controller*, mode u32, held-across-switch mask u32}. Frames, not time: a slow frame
// (a load, a hitch) must not end the menu mode.
MENU_FRAMES = 24    // a menu stays in effect this many frames after its last focused button (a list's focus blinks
                    // out for 6 to 24 frames as it scrolls)
    .text
    .p2align 2
    .globl _menu_tick
// Hook 1, replaces `pacibsp` at the entry of the menu screen update (main+0x2d1380, x0 = screen). The screen's
// entry list (+136 head, +144 first node, +156 entry offset from node, entry+24 button, button+56 focus state) as
// miojo-recomp's host/oot_menu.c reads it on the same build.
_menu_tick:
    stp x9, x10, [sp, #-48]!
    stp x11, x12, [sp, #16]
    stp x13, x14, [sp, #32]
    add x9, x0, #136
    ldrsw x10, [x0, #156]
    ldr x11, [x0, #144]
    mov w12, #512
1:  cbz x11, 3f
    cmp x11, x9
    b.eq 3f
    sub x13, x11, x10
    ldr x13, [x13, #24]
    cbz x13, 2f
    ldrb w14, [x13, #56]
    cbnz w14, 4f
2:  ldr x11, [x11, #8]
    subs w12, w12, #1
    b.ne 1b
    b 3f
FIX_STATE1:
4:  adrp x13, 0
    ldr w14, [x13, #4]
    str w14, [x13]
3:  ldp x13, x14, [sp, #32]
    ldp x11, x12, [sp, #16]
    ldp x9, x10, [sp], #48
    pacibsp
FIX_RET1:
    b .

    .p2align 2
    .globl _pad_swap
// Hook 2, replaces `ldr w3, [x19, #0x104]` in sead::Controller::calc (main+0x36a298), right after calcImpl has
// written this frame's hold bits (+0x114: bit 0 A, bit 1 B) and before trig / release / repeat are derived from it.
// Only the npad device controllers (vtable main+0x4c61b00): the merged controllers OR their children's hold bits.
_pad_swap:
    stp x9, x10, [sp, #-80]!
    stp x11, x12, [sp, #16]
    stp x13, x14, [sp, #32]
    stp x15, x16, [sp, #48]
    str x17, [sp, #64]
    ldr x9, [x19]
FIX_VT:
    adrp x10, 0
    add x10, x10, #0            // FIX_VT_LO (patched as the add's imm12)
    cmp x9, x10
    b.ne 9f
    ldr w9, [x19, #0x114]       // hold as the device reported it
FIX_STATE2:
    adrp x10, 0
    add x15, x10, #0x40
    mov w16, #16
5:  ldr x17, [x15]
    cmp x17, x19
    b.eq 6f
    cbz x17, 7f
    add x15, x15, #16
    subs w16, w16, #1
    b.ne 5b
    add x15, x10, #0x40         // table full: reuse slot 0
7:  str x19, [x15]
    mov w14, #0
    str w14, [x15, #8]
    str wzr, [x15, #12]
    b 8f
6:  add x16, x10, #0x40
    cmp x15, x16
    b.ne 12f
    ldr w16, [x10, #4]          // the first controller counts frames
    add w16, w16, #1
    str w16, [x10, #4]
12: ldr w11, [x10]              // mode = last menu frame != 0 && frame - last <= MENU_FRAMES
    ldr w12, [x10, #4]
    sub w12, w12, w11
    cmp w11, #0
    ccmp w12, #MENU_FRAMES, #2, ne
    cset w14, ls
    ldr w16, [x15, #8]
    ldr w17, [x15, #12]
    cmp w16, w14
    b.eq 10f
    str w14, [x15, #8]
    and w17, w9, #3             // mode changed: A/B held now stay ignored until released
10: and w17, w17, w9
    str w17, [x15, #12]
    bic w9, w9, w17
8:  cbz w14, 11f
    and w16, w9, #1             // menu: swap A and B
    ubfx w17, w9, #1, #1
    and w9, w9, #0xfffffffc
    orr w9, w9, w16, lsl #1
    orr w9, w9, w17
11: str w9, [x19, #0x114]
9:  ldr x17, [sp, #64]
    ldp x15, x16, [sp, #48]
    ldp x13, x14, [sp, #32]
    ldp x11, x12, [sp, #16]
    ldp x9, x10, [sp], #80
    ldr w3, [x19, #0x104]
FIX_RET2:
    b .

    .p2align 2
    .globl _xy_swap
// Western layout (build_mod.py --layout western, with the app's Buttons = Xbox, which maps every face button by its
// label): X and Y go back to their Nintendo positions, top = Switch X, left = Switch Y, everywhere. Same site as
// _pad_swap (main+0x36a298), same device controllers only; A/B stay as the host maps them (bottom = A).
_xy_swap:
    stp x9, x10, [sp, #-16]!
    ldr x9, [x19]
FIX_VT2:
    adrp x10, 0
    add x10, x10, #0
    cmp x9, x10
    b.ne 1f
    ldr w9, [x19, #0x114]
    eor w10, w9, w9, lsr #1     // bit 3 = X ^ Y
    and w10, w10, #8
    orr w10, w10, w10, lsl #1   // bits 3 and 4 when they differ
    eor w9, w9, w10
    str w9, [x19, #0x114]
1:  ldp x9, x10, [sp], #16
    ldr w3, [x19, #0x104]
FIX_RET3:
    b .

    .globl _ab_swap
// Western layout for an app without the Xbox / PlayStation button setting (upstream nxnative maps buttons by position,
// as Nintendo does: bottom = B): A and B trade places, so bottom = A and right = B, everywhere; X and Y stay at their
// Nintendo positions. Same site and controllers as _xy_swap.
_ab_swap:
    stp x9, x10, [sp, #-16]!
    ldr x9, [x19]
FIX_VT3:
    adrp x10, 0
    add x10, x10, #0
    cmp x9, x10
    b.ne 1f
    ldr w9, [x19, #0x114]
    eor w10, w9, w9, lsr #1     // bit 0 = A ^ B
    and w10, w10, #1
    orr w10, w10, w10, lsl #1   // bits 0 and 1 when they differ
    eor w9, w9, w10
    str w9, [x19, #0x114]
1:  ldp x9, x10, [sp], #16
    ldr w3, [x19, #0x104]
FIX_RET4:
    b .
