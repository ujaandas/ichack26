"use client"

import { useState } from "react"

import {
    AlertDialog,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"

const dialogMessages = [
    {
        title: "Welcome to Terraviz",
        description:
            "Terraviz is a geospatial visualization platform that helps individuals consolidate messy data and harness planetary insights to make informed decisions.",
    },
    {
        title: "Drawing your region",
        description:
            "Use the pen icon in the bottom-left corner to draw a polygon. This defines your area of interest.",
    },
    {
        title: "Processing your shape",
        description:
            "Once you confirm your shape, it's sent to our backend, evaluated by multiple models, and enriched with powerful geospatial data.",
    },
    {
        title: "Viewing insights",
        description:
            "Terraviz returns detailed insights, analytics, and visual layers to help you understand your region instantly.",
    },
]

export function AlertDialogDemo() {
    const hasSeen =
        typeof window !== "undefined" &&
        localStorage.getItem("tutorialSeen") === "true"

    const [open, setOpen] = useState(!hasSeen)
    const [step, setStep] = useState(0)

    const isLastStep = step === dialogMessages.length - 1
    const current = dialogMessages[step]

    const finishTutorial = () => {
        localStorage.setItem("tutorialSeen", "true")
        setOpen(false)
    }

    const handleContinue = () => {
        if (isLastStep) {
            finishTutorial()
            return
        }
        setStep(step + 1)
    }

    const handleSkip = () => {
        finishTutorial()
    }

    return (
        <AlertDialog open={open} onOpenChange={setOpen}>

            <AlertDialogContent>
                <AlertDialogHeader>
                    <AlertDialogTitle>{current.title}</AlertDialogTitle>
                    <AlertDialogDescription>
                        {current.description}
                    </AlertDialogDescription>
                </AlertDialogHeader>

                <AlertDialogFooter>
                    <AlertDialogCancel onClick={handleSkip}>
                        Skip
                    </AlertDialogCancel>

                    {/* IMPORTANT: Use Button, NOT AlertDialogAction */}
                    <Button onClick={handleContinue}>
                        {isLastStep ? "Finish" : "Continue"}
                    </Button>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    )
}
