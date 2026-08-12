"use client";

import React from "react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Palette, User, Bell, Moon, Sun, FileText } from "lucide-react";
import { useTheme } from "next-themes";

interface ConfiguracionModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onOpenPerfil: () => void;
  onOpenContrasena: () => void;
  workspaceActual?: any;
  onUpdateJurisdiccion?: (val: string) => void;
}

export function ConfiguracionModal({ open, onOpenChange, onOpenPerfil, onOpenContrasena, workspaceActual, onUpdateJurisdiccion }: ConfiguracionModalProps) {
  const [tabConfiguracion, setTabConfiguracion] = React.useState("apariencia");
  const { theme, setTheme } = useTheme();

  const toggleTheme = () => {
    setTheme(theme === "light" ? "dark" : "light");
  };



  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md bg-background border border-border shadow-xl">
        <DialogHeader>
          <DialogTitle>Configuración</DialogTitle>
          <DialogDescription>
            Personaliza tu experiencia en OfiSolve.
          </DialogDescription>
        </DialogHeader>

        <Tabs value={tabConfiguracion} onValueChange={setTabConfiguracion}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="apariencia">
              <Palette className="mr-2 h-4 w-4" />
              Apariencia
            </TabsTrigger>
            <TabsTrigger value="cuenta">
              <User className="mr-2 h-4 w-4" />
              Cuenta
            </TabsTrigger>
            {workspaceActual && (
              <TabsTrigger value="workspace">
                <FileText className="mr-2 h-4 w-4" />
                Workspace
              </TabsTrigger>
            )}
          </TabsList>

          {/* Tab: Apariencia */}
          <TabsContent value="apariencia" className="mt-4 space-y-4">
            <div className="flex items-center justify-between rounded-lg border border-border p-3">
              <div>
                <p className="text-sm font-medium text-foreground">Tema oscuro</p>
                <p className="text-xs text-muted-foreground">
                  Cambia entre modo claro y oscuro
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={toggleTheme}
              >
                {theme === "light" ? (
                  <Moon className="h-4 w-4" />
                ) : (
                  <Sun className="h-4 w-4" />
                )}
              </Button>
            </div>
          </TabsContent>

          {/* Tab: Cuenta */}
          <TabsContent value="cuenta" className="mt-4 space-y-4">
            <div className="flex items-center justify-between rounded-lg border border-border p-3">
              <div>
                <p className="text-sm font-medium text-foreground">Editar perfil</p>
                <p className="text-xs text-muted-foreground">
                  Actualiza tu nombre y datos
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  onOpenChange(false);
                  onOpenPerfil();
                }}
              >
                Editar
              </Button>
            </div>

            <div className="flex items-center justify-between rounded-lg border border-border p-3">
              <div>
                <p className="text-sm font-medium text-foreground">Contraseña</p>
                <p className="text-xs text-muted-foreground">
                  Cambia tu contraseña
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  onOpenChange(false);
                  onOpenContrasena();
                }}
              >
                Cambiar
              </Button>
            </div>
          </TabsContent>

          {/* Tab: Workspace */}
          {workspaceActual && onUpdateJurisdiccion && (
            <TabsContent value="workspace" className="mt-4 space-y-4">
              <div className="flex flex-col space-y-2 rounded-lg border border-border p-3">
                <p className="text-sm font-medium text-foreground">Jurisdicción de la IA ({workspaceActual.nombre})</p>
                <p className="text-xs text-muted-foreground mb-2">
                  Define bajo qué normativas provinciales redactará y auditará el asistente.
                </p>
                <select 
                  className="flex h-9 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                  value={workspaceActual.jurisdiccion || "CABA"}
                  onChange={(e) => onUpdateJurisdiccion(e.target.value)}
                >
                  <option value="CABA">CABA (Ciudad Autónoma de Buenos Aires)</option>
                  <option value="Provincia de Buenos Aires">Provincia de Buenos Aires</option>
                  <option value="Córdoba">Córdoba</option>
                  <option value="Santa Fe">Santa Fe</option>
                  <option value="Mendoza">Mendoza</option>
                  <option value="Nacional">Nacional (Genérico)</option>
                </select>
              </div>
            </TabsContent>
          )}

        </Tabs>

        <div className="mt-4 flex justify-end">
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cerrar
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
